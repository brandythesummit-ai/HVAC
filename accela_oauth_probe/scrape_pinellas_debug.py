#!/usr/bin/env python3
"""Debug version — save full response to a file so we can inspect."""
import requests, re
from bs4 import BeautifulSoup

BASE = "https://aca-prod.accela.com/PINELLAS"
SEARCH_URL = f"{BASE}/Cap/CapHome.aspx?module=Building&TabName=Home"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
})

print("GET initial page...")
r1 = session.get(SEARCH_URL, timeout=30)
print(f"  Status: {r1.status_code}, len: {len(r1.text)}")

# Save raw response for inspection
with open("/tmp/pinellas_initial.html", "w") as f:
    f.write(r1.text)

# Extract the form
soup = BeautifulSoup(r1.text, "html.parser")
form = soup.find("form", id="aspnetForm") or soup.find("form")
print(f"  Form found: {bool(form)}, action={form.get('action') if form else 'N/A'}")

# Find date input names
start_in = soup.find("input", {"name": re.compile(r"txtGSStartDate$")})
end_in = soup.find("input", {"name": re.compile(r"txtGSEndDate$")})
print(f"  Start date input: {start_in.get('name') if start_in else 'NOT FOUND'}")
print(f"  End date input:   {end_in.get('name') if end_in else 'NOT FOUND'}")

# Find all buttons/links that could be Search
search_candidates = []
for btn in soup.find_all(["a", "input", "button"]):
    name = btn.get("name", "")
    id_ = btn.get("id", "")
    val = btn.get("value", "") if btn.name == "input" else (btn.get_text() or "").strip()[:40]
    href = btn.get("href", "")
    onclick = btn.get("onclick", "")
    if any(x in (name + id_ + val).lower() for x in ["search", "newsearch", "btnnew", "gosearch"]):
        search_candidates.append({"tag": btn.name, "id": id_, "name": name, "val": val, "href": href[:80], "onclick": onclick[:80]})

print(f"\n  Search candidates ({len(search_candidates)}):")
for s in search_candidates[:10]:
    print(f"    {s}")

# Look for the record type dropdown
rt_select = soup.find("select", {"name": re.compile(r"ddlGSRecordType$")})
if rt_select:
    print(f"\n  Record type dropdown: {rt_select.get('name')}")
    options = rt_select.find_all("option")
    print(f"  Options ({len(options)} total, showing first 5 HVAC-related):")
    hvac = [o for o in options if "mechanical" in (o.get_text() or "").lower() or "air" in (o.get_text() or "").lower()]
    for o in hvac[:5]:
        print(f"    value='{o.get('value')}' text='{o.get_text().strip()}'")
else:
    print("\n  Record type dropdown: NOT FOUND with pattern ddlGSRecordType")
    # Look for alternatives
    selects = soup.find_all("select")
    print(f"  All selects ({len(selects)}):")
    for s in selects[:5]:
        print(f"    name={s.get('name')}  id={s.get('id')}")

# Check if login is required
if "login" in r1.text.lower()[:5000] and "password" in r1.text.lower()[:5000]:
    print("\n  ⚠️  Login form detected in page — may require authentication")

# Check for iframes (ACA sometimes loads search in an iframe)
iframes = soup.find_all("iframe")
if iframes:
    print(f"\n  iframes found: {len(iframes)}")
    for f in iframes:
        print(f"    src={f.get('src')}")
