#!/usr/bin/env python3
"""Path A feasibility test: can we programmatically query the HCFL legacy
PermitReports tool by folio number and extract HVAC permit data?"""
import requests, re, time
from bs4 import BeautifulSoup

BASE = "https://app.hillsboroughcounty.org/DevelopmentServices/PermitReports"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def fresh_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s

def try_search(session, searchType, searchBy, searchTerm, label):
    """Make a search request and report what we get back."""
    url = BASE
    params = {"searchType": searchType, "searchBy": searchBy, "searchTerm": searchTerm}
    t0 = time.time()
    r = session.get(url, params=params, timeout=30)
    elapsed = time.time() - t0
    soup = BeautifulSoup(r.text, "html.parser")

    # Check result containers
    containers = ["addressResults", "subResults", "folioResults", "permitResults", "results"]
    for cid in containers:
        el = soup.find(id=cid)
        if el:
            # Non-empty?
            inner_text = el.get_text(strip=True)
            child_tables = el.find_all("table")
            if inner_text or child_tables:
                return {
                    "label": label, "http": r.status_code, "elapsed_s": round(elapsed, 2),
                    "found_in": cid, "text_len": len(inner_text),
                    "table_count": len(child_tables),
                    "preview": inner_text[:300]
                }

    # Any tables at all?
    tables = soup.find_all("table")
    big_tables = [t for t in tables if len(t.find_all("tr")) > 2]

    # Any redirect/navigation hint
    if r.url != url and "searchTerm" not in r.url:
        return {"label": label, "http": r.status_code, "redirected_to": r.url[:120], "elapsed_s": round(elapsed, 2)}

    # Error/message scan
    text = soup.get_text(" ", strip=True)
    snippet = text[:400]

    # Record if the response has permit-looking content
    permit_patterns = re.findall(r'\b[A-Z]{3}\d{5}\b', text)  # MCH12345 style

    return {
        "label": label, "http": r.status_code, "elapsed_s": round(elapsed, 2),
        "big_tables": len(big_tables),
        "permit_patterns_found": len(permit_patterns),
        "sample_permits": permit_patterns[:5],
        "text_snippet": snippet[:300]
    }

print("=" * 80)
print("PATH A FEASIBILITY TEST — HCFL Legacy PermitReports tool")
print("=" * 80)

# Known Tampa addresses with high permit activity
tests = [
    ("Inspections", "oPermit", "MCH00001", "specific permit MCH00001 (3-letter prefix + 5 digits)"),
    ("Inspections", "oPermit", "BLD00001", "specific permit BLD00001"),
    ("Inspections", "oStreet", "KENNEDY", "street name KENNEDY"),
    ("Inspections", "oStreet", "HOWARD", "street name HOWARD"),
    ("Inspections", "oFolio", "1234567890", "generic folio (10 digits)"),
    ("Inspections", "oFolio", "123456-0000", "generic folio w/ dash"),
    ("Certificate", "oStreet", "KENNEDY", "Certificate of Occupancy by street"),
]

s = fresh_session()
print(f"\n{'Test':<65} {'HTTP':<6} {'Time':<7} {'Result'}")
print("-" * 120)
for searchType, searchBy, term, label in tests:
    try:
        r = try_search(s, searchType, searchBy, term, label)
        key_info = ""
        if r.get("found_in"):
            key_info = f"MATCH in #{r['found_in']}: tables={r['table_count']}, text_len={r['text_len']}"
        elif r.get("redirected_to"):
            key_info = f"REDIRECT → {r['redirected_to'][:60]}"
        elif r.get("permit_patterns_found"):
            key_info = f"perm_patterns={r['permit_patterns_found']}, sample={r.get('sample_permits',[])[:3]}"
        elif r.get("big_tables"):
            key_info = f"big_tables={r['big_tables']}"
        else:
            key_info = "no_results"
        print(f"{label[:65]:<65} {r.get('http','?')} {r.get('elapsed_s','?'):<7} {key_info[:70]}")
        time.sleep(0.5)  # polite delay
    except Exception as e:
        print(f"{label[:65]:<65} EXCEPTION: {str(e)[:60]}")
