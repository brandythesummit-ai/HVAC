#!/usr/bin/env python3
"""Validate which prefix(es) represent HVAC/Mechanical permits."""
import requests, re, time
from bs4 import BeautifulSoup

BASE = "https://app.hillsboroughcounty.org/DevelopmentServices/PermitReports"
SEARCH_URL = f"{BASE}/Search/GetResults"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "X-Requested-With": "XMLHttpRequest", "Referer": BASE})
    return s

def street_permits(s, street):
    r = s.get(SEARCH_URL, params={"searchBy": "oStreet", "searchTerm": street, "searchType": "Inspections"}, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")
    return [(row.find_all("td")[1].get_text(strip=True), row.find("a").get_text(strip=True))
            for row in soup.select("table.results tbody tr")
            if len(row.find_all("td")) >= 3 and row.find("a")]

def permit_detail_full(s, permit_no):
    """Fetch detail, dump full structured content for analysis."""
    for st in ["Inspections", "LHNC", "Electrical"]:
        r = s.get(f"{BASE}/Permit/{permit_no}/{st}", timeout=30)
        if r.status_code == 200 and permit_no in r.text:
            soup = BeautifulSoup(r.text, "html.parser")
            # Dump all labels + values from tables (ACA uses Label: Value rows often)
            data = {}
            # Try: find <p> or <span> pairs like "Label: Value"
            for el in soup.find_all(["p", "div", "span"]):
                t = el.get_text(strip=True)
                m = re.match(r"([A-Za-z /]+?)\s*:\s*(.+)$", t)
                if m and len(m.group(1)) < 40 and len(m.group(2)) < 200:
                    data[m.group(1).strip()] = m.group(2).strip()
            # Main title / header
            h = soup.find(["h1", "h2", "h3"])
            title = h.get_text(strip=True) if h else ""
            return {"title": title, "fields": data, "http": r.status_code, "searchType": st}
    return {"error": "not found in any searchType"}

# Collect permits from a few streets
print("Collecting permits from sample streets...")
s = session()
all_permits = []
for street in ["DALE MABRY", "NEBRASKA", "BUSCH"]:
    all_permits.extend(street_permits(s, street))
    time.sleep(0.4)

# Group by prefix (first 3 chars)
from collections import defaultdict
by_prefix = defaultdict(list)
for addr, perm in all_permits:
    # Extract prefix — handle both formats: "NME01234" and "21060178-H"
    m = re.match(r"^([A-Z]{2,4})\d", perm)
    if m:
        by_prefix[m.group(1)].append((addr, perm))
    elif perm[:1].isdigit():
        # Old-format permits like 21060178-H — treat as "OLD"
        by_prefix["OLD(digit-first)"].append((addr, perm))

print(f"\nPrefix buckets found: {sorted(by_prefix.keys())}")
print(f"Total permits collected: {sum(len(v) for v in by_prefix.values())}")

# For each prefix, pull one detail and show its title + key fields
targets = ["NME", "MCH", "CE1", "CE0", "NSG", "RFG", "NEL", "NCG", "FA0", "AS0"]
print(f"\n{'='*90}")
print("Inspecting one permit per prefix to identify HVAC/Mechanical")
print(f"{'='*90}")
for prefix in targets:
    if prefix not in by_prefix:
        print(f"  [{prefix}] no permits collected for this prefix")
        continue
    addr, perm = by_prefix[prefix][0]
    detail = permit_detail_full(s, perm)
    if detail.get("error"):
        print(f"  [{prefix}] {perm}: {detail['error']}")
        continue
    title = detail.get("title", "")
    # Pull a permit-type-ish field
    type_field = None
    for k, v in detail.get("fields", {}).items():
        lk = k.lower()
        if "type" in lk or "description" in lk or "work" in lk or "class" in lk:
            type_field = f"{k}: {v[:80]}"
            break
    print(f"  [{prefix}] {perm} @ {addr[:30]:<30} Title='{title[:40]}' | {type_field or '(no type field found)'}")
    time.sleep(0.4)
