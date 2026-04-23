#!/usr/bin/env python3
"""
Scrape Pinellas Accela Citizen Access portal to test how far back permit
data goes. Non-destructive — only reads, doesn't modify anything.

Approach:
1. GET search page, extract ASP.NET __VIEWSTATE / __EVENTVALIDATION tokens
2. POST a search with date range + permit type = Residential Mechanical
3. Parse result count
4. Repeat for multiple date ranges (2010, 2015, 2018, 2020, 2022, 2024)
5. Report which years return data
"""
import requests
from bs4 import BeautifulSoup
import re
import sys

BASE = "https://aca-prod.accela.com/PINELLAS"
SEARCH_URL = f"{BASE}/Cap/CapHome.aspx?module=Building&TabName=Home"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def pretty_count_result(html: str) -> dict:
    """Parse search result page and try to figure out how many permits were returned."""
    soup = BeautifulSoup(html, "html.parser")
    info = {"rows": 0, "summary": None, "has_results_table": False, "no_results": False}

    # Common Accela patterns:
    # - "Showing X-Y of Z"
    # - "No records found"
    # - <table id="...GridView..."> with <tr> rows
    text = soup.get_text(" ", strip=True)

    # No-results banner
    if re.search(r"no (records|results) (were )?found", text, re.I):
        info["no_results"] = True

    # "Showing 1-10 of 1,234" pattern
    m = re.search(r"Showing\s+\d+\s*-\s*\d+\s+of\s+([\d,]+)", text)
    if m:
        info["summary"] = m.group(0)
        info["total_estimated"] = int(m.group(1).replace(",", ""))

    # Count TRs inside any GridView
    grids = soup.select("table[id*='GridView'], table[class*='ACA_GridView']")
    if grids:
        info["has_results_table"] = True
        row_count = sum(len(g.select("tr")) for g in grids)
        info["rows"] = row_count

    return info

def extract_form_tokens(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    form_data = {}
    for inp in soup.find_all("input", type="hidden"):
        if inp.get("name"):
            form_data[inp["name"]] = inp.get("value", "")
    return form_data

def search_pinellas(session, start_date: str, end_date: str, record_type: str = ""):
    """Submit a date-range search and return result summary."""
    # Step 1: GET the search page to obtain the viewstate
    r1 = session.get(SEARCH_URL, timeout=30)
    r1.raise_for_status()

    tokens = extract_form_tokens(r1.text)
    # Find the Start Date and End Date input names by scanning the form
    soup = BeautifulSoup(r1.text, "html.parser")
    start_input = soup.find("input", {"name": re.compile(r"txtGSStartDate$")})
    end_input = soup.find("input", {"name": re.compile(r"txtGSEndDate$")})
    if not start_input or not end_input:
        return {"error": "Date input fields not found on search page"}

    start_name = start_input["name"]
    end_name = end_input["name"]

    # Find the Search button (usually an image or hyperlink triggering __doPostBack)
    # Accela typically has a "btnNewSearch" or similar
    search_btn = soup.find("a", id=re.compile(r"btnNewSearch"))
    if search_btn:
        # Extract the __doPostBack target
        onclick = search_btn.get("href", "")
        m = re.search(r"__doPostBack\('([^']+)'", onclick)
        event_target = m.group(1) if m else ""
    else:
        event_target = ""

    # Find the Record Type dropdown
    type_select = soup.find("select", {"name": re.compile(r"ddlGSRecordType$")})
    type_name = type_select["name"] if type_select else None

    # Step 2: Prepare form POST
    form_data = dict(tokens)
    form_data[start_name] = start_date
    form_data[end_name] = end_date
    form_data[f"{start_name}_ext_ClientState"] = (
        f'{{"maxDateJS":"new Date(9999,11,31,0,0,0,0)","minDateJS":"new Date(1,0,1,0,0,0,0)","enabled":true,"lastSetTextBoxValue":"{start_date}"}}'
    )
    form_data[f"{end_name}_ext_ClientState"] = (
        f'{{"maxDateJS":"new Date(9999,11,31,0,0,0,0)","minDateJS":"new Date(1,0,1,0,0,0,0)","enabled":true,"lastSetTextBoxValue":"{end_date}"}}'
    )
    if record_type and type_name:
        form_data[type_name] = record_type
    form_data["__EVENTTARGET"] = event_target
    form_data["__EVENTARGUMENT"] = ""

    # Step 3: POST
    r2 = session.post(SEARCH_URL, data=form_data, timeout=60, allow_redirects=True)
    r2.raise_for_status()

    return pretty_count_result(r2.text)

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    # First, warm up the session with a GET to establish cookies
    print("Warming up session with initial GET...")
    r0 = session.get(SEARCH_URL, timeout=30)
    print(f"  Status: {r0.status_code}, cookies: {len(session.cookies)}")

    test_ranges = [
        ("01/01/2024", "12/31/2024", "2024 - recent"),
        ("01/01/2022", "12/31/2022", "2022 - 3 yrs ago"),
        ("01/01/2020", "12/31/2020", "2020 - 5 yrs ago (API cutoff was here)"),
        ("01/01/2018", "12/31/2018", "2018 - 7 yrs ago (THIS is the question)"),
        ("01/01/2015", "12/31/2015", "2015 - 10 yrs ago"),
        ("01/01/2010", "12/31/2010", "2010 - 15 yrs ago"),
        ("01/01/2005", "12/31/2005", "2005 - 20 yrs ago"),
    ]

    print("\n" + "=" * 80)
    print("PINELLAS SCRAPER — date-depth probe (Residential Mechanical filter)")
    print("=" * 80)
    print(f"{'Date range':<40} {'Result':<60}")
    print("-" * 100)

    # Test WITHOUT record type filter first (baseline)
    for start, end, label in test_ranges:
        try:
            result = search_pinellas(session, start, end, record_type="Residential Mechanical")
            summary = result.get("summary") or (
                "NO RESULTS" if result.get("no_results") else
                f"rows={result['rows']}" if result.get("has_results_table") else "unparsed"
            )
            total = f" (total={result.get('total_estimated', '?')})" if result.get("total_estimated") else ""
            print(f"{label:<40} {summary}{total}")
        except Exception as e:
            print(f"{label:<40} EXCEPTION: {str(e)[:60]}")

if __name__ == "__main__":
    main()
