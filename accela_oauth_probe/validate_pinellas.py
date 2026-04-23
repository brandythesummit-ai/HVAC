#!/usr/bin/env python3
"""Validate PINELLAS Accela data using HCFL citizen account (cross-agency Accela account)."""
import os
import requests
from collections import Counter
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
USERNAME = os.getenv("ACCELA_HCFL_USERNAME")  # Same account, different agency
PASSWORD = os.getenv("ACCELA_HCFL_PASSWORD")

API_BASE = "https://apis.accela.com"
AGENCY = "PINELLAS"

print("=" * 80)
print(f"PINELLAS VALIDATION — using same credentials as HCFL")
print(f"Username: {USERNAME}  Agency: {AGENCY}  Env: PROD")
print("=" * 80)

# Step 1: Password grant for PINELLAS
print("\n[1/5] Password grant for PINELLAS...")
r = requests.post("https://auth.accela.com/oauth2/token",
    data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
          "username": USERNAME, "password": PASSWORD, "scope": "records",
          "agency_name": AGENCY, "environment": "PROD"},
    headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
    timeout=30)

if r.status_code != 200:
    print(f"  ❌ HTTP {r.status_code}: {r.text[:300]}")
    print(f"\n  Interpretation:")
    print(f"  - If 'invalid_user': account exists on HCFL but not Pinellas — need to register")
    print(f"  - If 'invalid_grant': password may be different, or account needs email confirmation")
    print(f"  - If 400: agency configuration issue")
    exit(1)

token = r.json()["access_token"]
print(f"  ✅ Got access token (expires in {r.json().get('expires_in', '?')}s)")

headers = {"Authorization": token, "Content-Type": "application/json",
           "x-accela-appid": CLIENT_ID, "x-accela-agency": AGENCY}

# Step 2: What modules does Pinellas expose? (We know portal uses DRS, but let's see)
print(f"\n[2/5] What modules does Pinellas expose? Testing module=Building and module=DRS...")
for module in ["Building", "DRS"]:
    r = requests.post(
        f"{API_BASE}/v4/search/records",
        params={"limit": 10, "offset": 0},
        json={"module": module, "openedDateFrom": "2025-01-01", "openedDateTo": "2025-12-31"},
        headers=headers, timeout=30)
    if r.status_code == 200:
        recs = r.json().get("result", [])
        print(f"  module='{module}': HTTP 200, {len(recs)} records")
        if recs:
            # Show type distribution
            types = Counter()
            for p in recs:
                t = p.get("type", {})
                tv = t.get("value") if isinstance(t, dict) else None
                if tv:
                    types[tv] += 1
            print(f"    Types seen: {dict(types.most_common(5))}")
    else:
        print(f"  module='{module}': HTTP {r.status_code} — {r.text[:150]}")

# Step 3: Data retention test — same as HCFL
print(f"\n[3/5] Date retention test — does Pinellas have the same ~5-year cutoff?")
# First find the right module
test_module = "Building"
recent_test = requests.post(
    f"{API_BASE}/v4/search/records",
    params={"limit": 1},
    json={"module": test_module, "openedDateFrom": "2025-01-01", "openedDateTo": "2025-12-31"},
    headers=headers, timeout=30)
if len(recent_test.json().get("result", []) or []) == 0:
    test_module = "DRS"
    print(f"  (Building is empty, switching to module=DRS)")

for year in ["2025", "2023", "2020", "2018", "2016", "2010"]:
    r = requests.post(
        f"{API_BASE}/v4/search/records",
        params={"limit": 5, "offset": 0},
        json={"module": test_module, "openedDateFrom": f"{year}-01-01", "openedDateTo": f"{year}-12-31"},
        headers=headers, timeout=30)
    try:
        count = len(r.json().get("result", []) or [])
    except Exception:
        count = "?"
    print(f"  {year}: {count} records (module={test_module})")

# Step 4: HVAC permit types for Pinellas
print(f"\n[4/5] What are the HVAC permit types in Pinellas?")
r = requests.post(
    f"{API_BASE}/v4/search/records",
    params={"limit": 200, "offset": 0},
    json={"module": test_module, "openedDateFrom": "2024-01-01", "openedDateTo": "2025-12-31"},
    headers=headers, timeout=60)
recs = r.json().get("result", [])
print(f"  Sampled {len(recs)} permits (module={test_module}, 2024-2025)")
types = Counter()
hvac_keywords = ["mechanical", "hvac", "air cond", "a/c"]
hvac_types = Counter()
for p in recs:
    t = p.get("type", {})
    tv = t.get("value") if isinstance(t, dict) else None
    tt = (t.get("text", "") or "") if isinstance(t, dict) else ""
    if tv:
        types[tv] += 1
        combined = (tv + " " + tt).lower()
        if any(kw in combined for kw in hvac_keywords):
            hvac_types[tv] += 1

print(f"\n  Top 15 permit types in {test_module} module:")
for t, c in types.most_common(15):
    print(f"    [{c:3d}] {t}")
print(f"\n  HVAC-related types found:")
for t, c in hvac_types.most_common():
    print(f"    [{c:3d}] {t}")

# Step 5: Try module=Building with just OR try detecting what Pinellas actually uses
# The web portal showed "Record Type" dropdown had things like "Site Plan Review", "Zoning Certification"
# Those are DRS things. For actual building permits, we might need a totally different module.
print(f"\n[5/5] Try other module names commonly used in Accela deployments...")
for m in ["BuildingPermits", "Permits", "Permit", "Licenses", "Contractor", "Inspections", "Planning"]:
    r = requests.post(
        f"{API_BASE}/v4/search/records",
        params={"limit": 3},
        json={"module": m, "openedDateFrom": "2025-01-01", "openedDateTo": "2025-12-31"},
        headers=headers, timeout=20)
    try:
        count = len(r.json().get("result", []) or [])
    except Exception:
        count = "?"
    print(f"  module='{m}': HTTP {r.status_code}, count={count}")

print("\n" + "=" * 80)
print("DONE.")
print("=" * 80)
