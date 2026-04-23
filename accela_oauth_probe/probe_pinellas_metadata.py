#!/usr/bin/env python3
"""
Probe PINELLAS agency metadata using only app credentials (no user login).
Also test whether HCFL's data cutoff is Accela-wide or agency-specific by
trying different date fields and endpoints.
"""
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")

API_BASE = "https://apis.accela.com"

# Headers for app-credentialed (no user token) endpoints
APP_HEADERS = {
    "x-accela-appid": CLIENT_ID,
    "x-accela-appsecret": CLIENT_SECRET,
    "Content-Type": "application/json",
}

print("=" * 80)
print("PART 1: PINELLAS AGENCY METADATA (no user auth needed)")
print("=" * 80)

# 1. Agency info
for path in ["/v4/agencies/PINELLAS", "/v4/agencies/PINELLAS/environments"]:
    r = requests.get(f"{API_BASE}{path}", headers=APP_HEADERS, timeout=30)
    print(f"\nGET {path}")
    print(f"  HTTP {r.status_code}")
    try:
        data = r.json()
        result = data.get("result")
        if isinstance(result, dict):
            # Agency info
            print(f"  name: {result.get('name')}")
            print(f"  display: {result.get('display')}")
            print(f"  state: {result.get('state')}")
            print(f"  enabled: {result.get('enabled')}")
            print(f"  hostedACA: {result.get('hostedACA')}")
        elif isinstance(result, list):
            # Environments list
            names = [e.get('name') for e in result]
            print(f"  environments ({len(names)}): {names}")
    except Exception as e:
        print(f"  Parse error: {e}")
        print(f"  Body preview: {r.text[:200]}")

# 2. HCFL comparison (we know this works)
for path in ["/v4/agencies/HCFL", "/v4/agencies/HCFL/environments"]:
    r = requests.get(f"{API_BASE}{path}", headers=APP_HEADERS, timeout=30)
    print(f"\n[CONTROL] GET {path}")
    print(f"  HTTP {r.status_code}")
    try:
        data = r.json()
        result = data.get("result")
        if isinstance(result, list):
            names = [e.get('name') for e in result]
            print(f"  environments ({len(names)}): {names[:6]}...")
    except Exception:
        pass

print("\n" + "=" * 80)
print("PART 2: HCFL DATA CUTOFF INVESTIGATION — is this Accela-wide or HCFL-specific?")
print("=" * 80)

# Get HCFL token
r = requests.post(
    "https://auth.accela.com/oauth2/token",
    data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
          "username": os.getenv("ACCELA_HCFL_USERNAME"), "password": os.getenv("ACCELA_HCFL_PASSWORD"),
          "scope": "records", "agency_name": "HCFL", "environment": "PROD"},
    headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
    timeout=30)
r.raise_for_status()
token = r.json()["access_token"]
user_headers = {"Authorization": token, "Content-Type": "application/json",
                "x-accela-appid": CLIENT_ID, "x-accela-agency": "HCFL"}

# Test A: Does the CUTOFF apply to completedDateFrom/To as well?
print("\nTEST A: Try filtering by COMPLETED date instead of OPENED date")
for date_field_prefix, year in [("completedDate", "2017"), ("completedDate", "2024"), ("statusDate", "2017"), ("statusDate", "2024")]:
    body = {
        "module": "Building",
        f"{date_field_prefix}From": f"{year}-01-01",
        f"{date_field_prefix}To": f"{year}-12-31",
    }
    r = requests.post(
        f"{API_BASE}/v4/search/records",
        params={"limit": 5},
        json=body, headers=user_headers, timeout=30)
    try:
        data = r.json()
        count = len(data.get("result", []) or [])
    except Exception:
        count = "parse_err"
    print(f"  {date_field_prefix}From/To {year}: HTTP {r.status_code}, records={count}")

# Test B: Try the GET /v4/records endpoint (different endpoint, might behave differently)
print("\nTEST B: Try GET /v4/records (instead of POST /v4/search/records)")
for year in ["2017", "2020", "2024"]:
    r = requests.get(
        f"{API_BASE}/v4/records",
        params={
            "module": "Building",
            "openedDateFrom": f"{year}-01-01",
            "openedDateTo": f"{year}-12-31",
            "limit": 5,
        },
        headers=user_headers, timeout=30)
    try:
        data = r.json()
        count = len(data.get("result", []) or [])
    except Exception:
        count = "parse_err"
    print(f"  GET /v4/records {year}: HTTP {r.status_code}, records={count}")

# Test C: Try looking up a specific older record directly (by knowing a customId format)
print("\nTEST C: Try fetching specific older customIds directly (bypasses date search)")
# HCFL format appears to be HC-BLD-YY-NNNNNNN or HC-BTR-YY-NNNNNNN. Let's try 2018 IDs.
for cid in ["HC-BLD-18-0000001", "HC-BTR-18-0000001", "BLD18-00001"]:
    r = requests.get(
        f"{API_BASE}/v4/records",
        params={"customId": cid, "module": "Building", "limit": 1},
        headers=user_headers, timeout=30)
    try:
        data = r.json()
        count = len(data.get("result", []) or [])
    except Exception:
        count = "parse_err"
    print(f"  customId '{cid}': HTTP {r.status_code}, records={count}")

# Test D: Check the record types endpoint — is there a clue about what's indexed?
print("\nTEST D: Agency record types (what categories does HCFL expose via API?)")
r = requests.get(
    f"{API_BASE}/v4/agencies/HCFL/recordTypes",
    params={"module": "Building", "limit": 50},
    headers=user_headers, timeout=30)
print(f"  HTTP {r.status_code}")
try:
    data = r.json()
    types = data.get("result", []) or []
    print(f"  Total record types returned: {len(types)}")
    # Show mechanical-related ones
    mech = [t for t in types if 'mechanical' in (t.get('value','') + t.get('text','')).lower()]
    print(f"  Mechanical-related types ({len(mech)}):")
    for t in mech:
        print(f"    value='{t.get('value')}' text='{t.get('text')}'")
except Exception as e:
    print(f"  Parse err: {e}")

print("\n" + "=" * 80)
print("INTERPRETATION")
print("=" * 80)
print("""
If completedDate/statusDate also show 0 pre-2020 → Accela agency-side purges ALL pre-2020
If GET /v4/records returns pre-2020 records → POST search endpoint has a cutoff, GET doesn't
If customId direct lookup returns pre-2020 records → data exists, just not searchable
If agency recordTypes list is populated → app has full scope, just data is gated
""")
