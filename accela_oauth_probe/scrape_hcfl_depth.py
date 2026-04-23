#!/usr/bin/env python3
"""Scrape HCFL's public portal and compare depth to what the API gives us.
HCFL's API pulled 19K permits going back to 1996 via year-by-year loop.
Let's see what the public portal returns for the same range + type."""
import requests, re
from bs4 import BeautifulSoup

BASE = "https://aca-prod.accela.com/HCFL"
SEARCH_URL = f"{BASE}/Cap/CapHome.aspx?module=Building&TabName=Home"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def fresh_session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    return s

def get_form_and_types(session):
    r1 = session.get(SEARCH_URL, timeout=30)
    r1.raise_for_status()
    soup = BeautifulSoup(r1.text, "html.parser")
    form = {}
    for el in soup.find_all(["input","select"]):
        n = el.get("name")
        if not n: continue
        if el.name == "input":
            if el.get("type","").lower() in ("submit","image"): continue
            form[n] = el.get("value","") or ""
        else:
            opt = el.find("option", selected=True) or el.find("option")
            form[n] = opt.get("value","") if opt else ""

    # Also return all permit type options for inspection
    pt = soup.find("select", {"name": re.compile(r"ddlGSPermitType$")})
    opts = []
    if pt:
        for o in pt.find_all("option"):
            opts.append({"value": o.get("value",""), "text": o.get_text(strip=True)})
    return form, opts

def search(session, start, end, permit_type_value=""):
    form, _ = get_form_and_types(session)
    P = "ctl00$PlaceHolderMain$generalSearchForm"
    form[f"{P}$txtGSStartDate"] = start
    form[f"{P}$txtGSEndDate"] = end
    if permit_type_value:
        form[f"{P}$ddlGSPermitType"] = permit_type_value
    form["__EVENTTARGET"] = "ctl00$PlaceHolderMain$btnNewSearch"
    form["__EVENTARGUMENT"] = ""
    r2 = session.post(SEARCH_URL, data=form, headers={
        "Content-Type":"application/x-www-form-urlencoded",
        "Origin":"https://aca-prod.accela.com","Referer":SEARCH_URL,
    }, timeout=60)
    return r2

def parse_summary(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    m = re.search(r"Showing\s+\d+\s*[-–]\s*\d+\s+of\s+([\d,]+\+?)", text)
    total = m.group(1) if m else None
    grid = soup.find("table", id=re.compile(r"gdvPermitList"))
    rows = []
    if grid:
        for r_ in grid.find_all("tr")[2:]:
            cells = [c.get_text(strip=True) for c in r_.find_all("td")]
            if len(cells) >= 4 and re.match(r"\d{2}/\d{2}/\d{4}", cells[1] or ""):
                rows.append({"date": cells[1], "recno": cells[3], "type": cells[2]})
    return {"total": total, "rows": rows}

# Phase 1: discover HCFL's HVAC-related permit types
print("=" * 100)
print("PHASE 1: HCFL portal dropdown — find HVAC-related permit types")
print("=" * 100)
s = fresh_session()
_, types = get_form_and_types(s)
print(f"Total permit types in dropdown: {len(types)}")
hvac = [t for t in types if any(kw in t["text"].lower() for kw in ["mechanical","hvac","a/c","air"])]
print(f"\nHVAC-related types ({len(hvac)}):")
for t in hvac:
    print(f"  value='{t['value']}' | text='{t['text']}'")

# Phase 2: depth test per HVAC type + year
print(f"\n{'='*100}")
print("PHASE 2: HCFL portal — permits per year, per HVAC type")
print(f"{'='*100}")
years = [2024, 2020, 2018, 2015, 2012, 2010, 2005, 2000, 1995]

if hvac:
    # Pick first HVAC type for depth test
    test_type = hvac[0]
    print(f"\nTesting type: value='{test_type['value']}' (text='{test_type['text']}')")
    print(f"{'Year':<6} {'Total':<10} Sample (first row)")
    print("-" * 80)
    for y in years:
        s = fresh_session()
        r = search(s, f"01/01/{y}", f"12/31/{y}", permit_type_value=test_type["value"])
        info = parse_summary(r.text)
        sample = info["rows"][0] if info["rows"] else None
        sample_str = f"{sample['date']} | {sample['recno']} | {sample['type'][:40]}" if sample else "-"
        print(f"{y:<6} {str(info['total'] or '-'):<10} {sample_str}")

# Phase 3: all-Building depth (control)
print(f"\n{'='*100}")
print("PHASE 3: HCFL all-Building depth (control — no type filter)")
print(f"{'='*100}")
print(f"{'Year':<6} {'Total':<10} Sample (first row)")
print("-" * 80)
for y in years:
    s = fresh_session()
    r = search(s, f"01/01/{y}", f"12/31/{y}", permit_type_value="")
    info = parse_summary(r.text)
    sample = info["rows"][0] if info["rows"] else None
    sample_str = f"{sample['date']} | {sample['recno']} | {sample['type'][:40]}" if sample else "-"
    print(f"{y:<6} {str(info['total'] or '-'):<10} {sample_str}")
