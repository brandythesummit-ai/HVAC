#!/usr/bin/env python3
"""Pinellas permit scraper V3 — WORKING. Maps date ranges → result counts."""
import requests, re
from bs4 import BeautifulSoup

BASE = "https://aca-prod.accela.com/PINELLAS"
SEARCH_URL = f"{BASE}/Cap/CapHome.aspx?module=Building&TabName=Home"

def build_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s

def search(session, start_date, end_date, permit_type_value="Building/Res/Mechanical/NA"):
    r1 = session.get(SEARCH_URL, timeout=30)
    r1.raise_for_status()
    soup = BeautifulSoup(r1.text, "html.parser")
    form_data = {}
    for el in soup.find_all(["input", "select", "textarea"]):
        n = el.get("name")
        if not n: continue
        if el.name == "input":
            if el.get("type", "").lower() in ("submit", "image"): continue
            form_data[n] = el.get("value", "") or ""
        elif el.name == "select":
            opt = el.find("option", selected=True) or el.find("option")
            form_data[n] = opt.get("value", "") if opt else ""
    P = "ctl00$PlaceHolderMain$generalSearchForm"
    form_data[f"{P}$txtGSStartDate"] = start_date
    form_data[f"{P}$txtGSEndDate"] = end_date
    if permit_type_value:
        form_data[f"{P}$ddlGSPermitType"] = permit_type_value
    form_data["__EVENTTARGET"] = "ctl00$PlaceHolderMain$btnNewSearch"
    form_data["__EVENTARGUMENT"] = ""

    r2 = session.post(SEARCH_URL, data=form_data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://aca-prod.accela.com",
        "Referer": SEARCH_URL,
    }, timeout=60)
    return r2

def parse_results(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    # Count summary
    m = re.search(r"Showing\s+(\d+)\s*[-–]\s*(\d+)\s+of\s+([\d,]+\+?)", text)
    if m:
        total = m.group(3)
    else:
        total = None
    no_results = bool(re.search(r"no\s+records?\s+(found|match)", text, re.I))

    # Extract sample permit rows from the grid
    grid = soup.find("table", id=re.compile(r"gdvPermitList$"))
    sample_rows = []
    earliest_date = None
    latest_date = None
    if grid:
        for row in grid.find_all("tr")[2:]:  # skip header + caption
            cells = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cells) >= 4 and cells[1]:
                # Column 1 = Date, 2 = Record Type, 3 = Record Number, 4 = Status
                date_str = cells[1]
                # Parse date like "07/03/2024"
                if re.match(r"\d{2}/\d{2}/\d{4}", date_str):
                    # Normalize to YYYY-MM-DD for comparison
                    parts = date_str.split("/")
                    iso = f"{parts[2]}-{parts[0]}-{parts[1]}"
                    if earliest_date is None or iso < earliest_date:
                        earliest_date = iso
                    if latest_date is None or iso > latest_date:
                        latest_date = iso
                    if len(sample_rows) < 3:
                        sample_rows.append({"date": date_str, "type": cells[2][:30], "recno": cells[3][:15], "status": cells[4][:15] if len(cells) > 4 else ""})

    return {
        "total": total,
        "no_results": no_results,
        "earliest_date_in_first_page": earliest_date,
        "latest_date_in_first_page": latest_date,
        "sample_rows": sample_rows,
    }

def main():
    session = build_session()

    print("=" * 100)
    print("PINELLAS SCRAPER V3 — Residential Mechanical permits depth test")
    print("=" * 100)

    test_ranges = [
        ("01/01/2024", "12/31/2024", "2024"),
        ("01/01/2022", "12/31/2022", "2022"),
        ("01/01/2020", "12/31/2020", "2020"),
        ("01/01/2018", "12/31/2018", "2018"),
        ("01/01/2015", "12/31/2015", "2015"),
        ("01/01/2012", "12/31/2012", "2012"),
        ("01/01/2010", "12/31/2010", "2010"),
        ("01/01/2005", "12/31/2005", "2005"),
        ("01/01/2000", "12/31/2000", "2000"),
    ]

    print(f"\n{'Year':<7} {'Total':<10} {'Earliest':<12} {'Latest':<12} Sample permit")
    print("-" * 100)

    for start, end, label in test_ranges:
        try:
            r = search(session, start, end)
            info = parse_results(r.text)
            total = info.get("total") or ("NO RESULTS" if info["no_results"] else "?")
            earliest = info.get("earliest_date_in_first_page") or "-"
            latest = info.get("latest_date_in_first_page") or "-"
            sample = info["sample_rows"][0] if info["sample_rows"] else None
            sample_str = f"{sample['date']} | {sample['recno']} | {sample['type']}" if sample else ""
            print(f"{label:<7} {str(total):<10} {earliest:<12} {latest:<12} {sample_str}")
        except Exception as e:
            print(f"{label:<7} EXCEPTION: {str(e)[:80]}")

if __name__ == "__main__":
    main()
