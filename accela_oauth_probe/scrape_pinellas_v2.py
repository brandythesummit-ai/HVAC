#!/usr/bin/env python3
"""Scrape Pinellas permits — V2 with correct form field names.
Date-depth test: how far back can we pull Residential Mechanical permits?"""
import requests, re, sys
from bs4 import BeautifulSoup

BASE = "https://aca-prod.accela.com/PINELLAS"
SEARCH_URL = f"{BASE}/Cap/CapHome.aspx?module=Building&TabName=Home"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def search(session, start_date, end_date, permit_type_value="Building/Res/Mechanical/NA"):
    # Step 1: GET search page
    r1 = session.get(SEARCH_URL, timeout=30)
    r1.raise_for_status()
    soup = BeautifulSoup(r1.text, "html.parser")

    # Extract all hidden inputs (viewstate + tokens)
    form_data = {}
    for inp in soup.find_all("input", type="hidden"):
        if inp.get("name"):
            form_data[inp["name"]] = inp.get("value", "")

    # Fill date and permit type fields
    PREFIX = "ctl00$PlaceHolderMain$generalSearchForm"
    form_data[f"{PREFIX}$txtGSStartDate"] = start_date
    form_data[f"{PREFIX}$txtGSEndDate"] = end_date
    form_data[f"{PREFIX}$txtGSStartDate_ext_ClientState"] = ""
    form_data[f"{PREFIX}$txtGSEndDate_ext_ClientState"] = ""
    form_data[f"{PREFIX}$ddlGSPermitType"] = permit_type_value

    # Fill empty required inputs that the form expects
    for inp in soup.find_all("input", type="text"):
        name = inp.get("name")
        if name and name not in form_data:
            form_data[name] = inp.get("value", "") or ""

    # Search type dropdown — ensure it's set to permit search
    st = soup.find("select", {"name": re.compile(r"ddlSearchType$")})
    if st and st.get("name"):
        # First option is usually "Permit/Record"
        first_val = st.find("option").get("value", "") if st.find("option") else ""
        form_data[st["name"]] = form_data.get(st["name"]) or first_val

    # ASP.NET __doPostBack target for the Search button
    form_data["__EVENTTARGET"] = "ctl00$PlaceHolderMain$btnNewSearch"
    form_data["__EVENTARGUMENT"] = ""

    # Step 2: POST
    r2 = session.post(SEARCH_URL, data=form_data, timeout=60, allow_redirects=True)
    return r2

def summarize(html, date_label):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    # Look for "Showing X-Y of Z" or count
    m = re.search(r"Showing\s+\d+\s*[-–]\s*\d+\s+of\s+([\d,]+)", text)
    total = None
    if m:
        total = int(m.group(1).replace(",", ""))

    # "No records found" / "No results"
    no_results = bool(re.search(r"(no\s+records?\s+(found|match)|no\s+results)", text, re.I))

    # Find results table — ACA_GridView or "tblResults" patterns
    grids = soup.select("table.ACA_GridView, table[id*='gdvPermitList'], table[class*='CapList']")
    row_count = 0
    sample = []
    for g in grids:
        rows = g.select("tr")
        row_count += len(rows)
        # Try to pull record numbers from first few rows
        for row in rows[:3]:
            # Record IDs are usually in the 2nd column as links
            cells = row.find_all("td")
            if cells:
                cell_texts = [c.get_text(strip=True)[:30] for c in cells[:4]]
                if any(cell_texts):
                    sample.append(" | ".join(cell_texts))

    # Detect common error strings
    has_error = "error" in text.lower()[:200]
    has_max_results = "maximum" in text.lower() or "too many" in text.lower()

    return {
        "total": total,
        "no_results": no_results,
        "grid_rows": row_count,
        "max_results_warning": has_max_results,
        "has_error": has_error,
        "sample": sample[:2],
        "html_len": len(html),
    }

def main():
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    print("Warming up session...")
    session.get(SEARCH_URL, timeout=30)

    test_ranges = [
        ("01/01/2024", "12/31/2024", "2024"),
        ("01/01/2022", "12/31/2022", "2022"),
        ("01/01/2020", "12/31/2020", "2020"),
        ("01/01/2018", "12/31/2018", "2018"),
        ("01/01/2015", "12/31/2015", "2015"),
        ("01/01/2010", "12/31/2010", "2010"),
        ("01/01/2005", "12/31/2005", "2005"),
    ]

    print(f"\n{'='*95}")
    print("PINELLAS PORTAL SCRAPE — Residential Mechanical permits by year")
    print("="*95)
    print(f"{'Year':<7} {'Total':<10} {'Rows':<7} {'No-results':<12} {'Sample':<50}")
    print("-"*95)

    for start, end, label in test_ranges:
        try:
            r = search(session, start, end, permit_type_value="Building/Res/Mechanical/NA")
            info = summarize(r.text, label)
            no_res = "YES" if info["no_results"] else "no"
            total_str = str(info["total"]) if info["total"] else "-"
            sample_str = info["sample"][0][:48] if info["sample"] else ""
            print(f"{label:<7} {total_str:<10} {info['grid_rows']:<7} {no_res:<12} {sample_str}")
        except Exception as e:
            print(f"{label:<7} EXCEPTION: {e}")

if __name__ == "__main__":
    main()
