#!/usr/bin/env python3
"""Proof-of-concept end-to-end HCFL legacy scraper.
1. Query a street name → get permit list
2. For each permit, fetch detail page → parse type, date, status
3. Report results
"""
import requests, re, time
from bs4 import BeautifulSoup

BASE = "https://app.hillsboroughcounty.org/DevelopmentServices/PermitReports"
SEARCH_URL = f"{BASE}/Search/GetResults"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def fresh_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BASE,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s

def search_by_street(session, street, search_type="Inspections"):
    """Return list of (street_address, permit_number) tuples."""
    r = session.get(SEARCH_URL, params={
        "searchBy": "oStreet",
        "searchTerm": street,
        "searchType": search_type,
    }, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for row in soup.select("table.results tbody tr"):
        cells = row.find_all("td")
        if len(cells) >= 3:
            address = cells[1].get_text(strip=True)
            link = cells[2].find("a")
            if link:
                permit_no = link.get_text(strip=True)
                href = link.get("href", "")
                rows.append({"address": address, "permit": permit_no, "href": href})
    return rows

def get_permit_detail(session, permit_number, search_type="Inspections"):
    """Fetch a specific permit's detail page and parse key fields."""
    url = f"{BASE}/Permit/{permit_number}/{search_type}"
    r = session.get(url, timeout=30)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}"}
    soup = BeautifulSoup(r.text, "html.parser")
    # Dump all visible labels and values (ASP.NET / ACA pages use label:value structure)
    text = soup.get_text("\n", strip=True)

    # Try to extract common fields
    fields = {}
    # Safe regex extract — skip patterns that don't match, don't crash
    for pattern, key in [
        (r"(?:Permit|Project)\s*(?:Number|#|No\.?):?\s*([A-Z0-9-]+)", "permit_no"),
        (r"(?:Permit|Project)\s*Type:?\s*([^\n]+)", "permit_type"),
        (r"Address:?\s*([^\n]+)", "address"),
        (r"(?:Opened|Issue|Application|Received)\s*Date:?\s*(\d{1,2}/\d{1,2}/\d{4})", "opened_date"),
        (r"Status:?\s*([^\n]{1,40})", "status"),
        (r"Owner:?\s*([^\n]{1,60})", "owner"),
        (r"(?:Parcel|Folio)(?:\s*#|\s*Number)?:?\s*([0-9-]+)", "folio"),
        (r"Job\s*(?:Value|Cost|Amount):?\s*\$?\s*([\d,\.]+)", "job_value"),
        (r"Description:?\s*([^\n]{0,120})", "description"),
    ]:
        try:
            m = re.search(pattern, text, re.I)
            if m and m.group(1):
                fields[key] = m.group(1).strip()
        except (IndexError, AttributeError):
            pass

    # Also collect all tables on page — may have structured data
    tables = soup.find_all("table")
    table_info = []
    for t in tables:
        rows = t.find_all("tr")
        if len(rows) >= 2:
            table_info.append({"rows": len(rows), "headers": [h.get_text(strip=True) for h in t.find_all("th")[:6]]})

    return {
        "permit_number": permit_number,
        "parsed_fields": fields,
        "tables_on_page": len(table_info),
        "table_samples": table_info[:3],
        "response_size": len(r.text),
    }

print("=" * 90)
print("END-TO-END POC: HCFL Legacy Scraper")
print("=" * 90)

session = fresh_session()

# Phase 1: Street search — pick a known Tampa HVAC-heavy street
test_streets = ["HARBOUR ISLAND", "KENNEDY BLVD", "DALE MABRY", "NEBRASKA", "BUSCH"]

print("\nPhase 1: Street-name search volume test\n")
all_permits = []
for street in test_streets:
    try:
        t0 = time.time()
        results = search_by_street(session, street)
        dt = time.time() - t0
        print(f"  Street '{street}': {len(results)} permits returned ({dt:.2f}s)")
        all_permits.extend(results)
        time.sleep(0.5)  # polite
    except Exception as e:
        print(f"  Street '{street}': ERROR {e}")

# Pick unique permits up to 5
seen = set()
unique_permits = []
for p in all_permits:
    if p["permit"] not in seen:
        seen.add(p["permit"])
        unique_permits.append(p)
    if len(unique_permits) >= 5:
        break

# Filter to likely HVAC: MCH (Mechanical), or check all
print(f"\nTotal unique permits from all street searches: {len(set(p['permit'] for p in all_permits))}")
print(f"Prefix distribution (first 3 chars):")
from collections import Counter
prefixes = Counter(p['permit'][:3] for p in all_permits if p['permit'])
for prefix, count in prefixes.most_common(10):
    print(f"    {prefix}: {count}")

# Phase 2: Pull details for 5 permits
print("\nPhase 2: Permit detail extraction")
print("-" * 90)
for p in unique_permits:
    print(f"\n  Permit: {p['permit']} @ {p['address']}")
    t0 = time.time()
    detail = get_permit_detail(session, p["permit"])
    dt = time.time() - t0
    print(f"    Time: {dt:.2f}s, Response: {detail.get('response_size','?')}B")
    fields = detail.get("parsed_fields", {})
    for k, v in fields.items():
        print(f"    {k}: {v[:80]}")
    if detail.get("table_samples"):
        print(f"    Tables on page: {detail['tables_on_page']}")
        for t in detail["table_samples"][:2]:
            print(f"      rows={t['rows']}, headers={t['headers']}")
    time.sleep(0.5)
