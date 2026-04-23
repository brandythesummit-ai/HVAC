#!/usr/bin/env python3
"""Test multiple date ranges to diagnose why HCFL returned zero permits for 2016-2018."""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
USERNAME = os.getenv("ACCELA_HCFL_USERNAME")
PASSWORD = os.getenv("ACCELA_HCFL_PASSWORD")
API_BASE = "https://apis.accela.com"

# Get token
r = requests.post(
    "https://auth.accela.com/oauth2/token",
    data={
        "grant_type": "password",
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "username": USERNAME, "password": PASSWORD,
        "scope": "records", "agency_name": "HCFL", "environment": "PROD",
    },
    headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
    timeout=30,
)
r.raise_for_status()
access_token = r.json()["access_token"]
print(f"✅ Token: {access_token[:15]}... (expires 900s)")

test_cases = [
    ("2026-04-01", "2026-04-20", "Last 3 weeks (very recent)"),
    ("2026-01-01", "2026-04-20", "2026 YTD"),
    ("2025-01-01", "2025-12-31", "All of 2025"),
    ("2024-01-01", "2024-12-31", "All of 2024"),
    ("2023-01-01", "2023-12-31", "2023"),
    ("2022-01-01", "2022-12-31", "2022"),
    ("2020-01-01", "2020-12-31", "2020"),
    ("2018-01-01", "2018-12-31", "2018 (Signal A target)"),
    ("2016-01-01", "2016-12-31", "2016 (Signal A deep)"),
    ("2010-01-01", "2010-12-31", "2010 (historical)"),
]

def search(date_from, date_to, with_type=False):
    body = {"module": "Building", "openedDateFrom": date_from, "openedDateTo": date_to}
    if with_type:
        body["type"] = {"value": "Residential Mechanical Trade Permit"}
    r = requests.post(
        f"{API_BASE}/v4/search/records",
        params={"limit": 5, "offset": 0},
        json=body,
        headers={
            "Authorization": access_token,
            "Content-Type": "application/json",
            "x-accela-appid": CLIENT_ID,
            "x-accela-agency": "HCFL",
        },
        timeout=30,
    )
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text}
    return r.status_code, data, r.headers

print(f"\n{'='*80}")
print(f"TESTING DATE RANGES — NO TYPE FILTER (all Building permits)")
print(f"{'='*80}")
print(f"{'Date range':<30} {'Status':<8} {'Count':<8} {'Total':<8} Notes")

for date_from, date_to, label in test_cases:
    try:
        status, data, headers = search(date_from, date_to, with_type=False)
        result = data.get("result") if isinstance(data, dict) else None
        total = data.get("total") if isinstance(data, dict) else None
        count = len(result) if isinstance(result, list) else "?"
        rate = headers.get('x-ratelimit-remaining', '-')
        err = ""
        if status != 200:
            err = f" ERR: {str(data)[:80]}"
        print(f"  {label:<28} {status:<8} {str(count):<8} {str(total):<8} rate={rate}{err}")
    except Exception as e:
        print(f"  {label:<28} EXCEPTION: {e}")

print(f"\n{'='*80}")
print(f"SECOND PASS — WITH type='Residential Mechanical Trade Permit'")
print(f"{'='*80}")
for date_from, date_to, label in test_cases[:5]:
    status, data, headers = search(date_from, date_to, with_type=True)
    result = data.get("result") if isinstance(data, dict) else None
    total = data.get("total") if isinstance(data, dict) else None
    count = len(result) if isinstance(result, list) else "?"
    print(f"  {label:<28} {status:<8} {str(count):<8} {str(total):<8}")

# ALSO: try a smaller date range with NO date filter at all to see if filter is broken
print(f"\n{'='*80}")
print(f"CONTROL — NO date filter, just module=Building")
print(f"{'='*80}")
r2 = requests.post(
    f"{API_BASE}/v4/search/records",
    params={"limit": 5, "offset": 0},
    json={"module": "Building"},
    headers={
        "Authorization": access_token,
        "Content-Type": "application/json",
        "x-accela-appid": CLIENT_ID,
        "x-accela-agency": "HCFL",
    },
    timeout=30,
)
data2 = r2.json() if r2.headers.get("content-type", "").startswith("application/json") else {"raw": r2.text[:200]}
result2 = data2.get("result") if isinstance(data2, dict) else None
count2 = len(result2) if isinstance(result2, list) else "?"
total2 = data2.get("total") if isinstance(data2, dict) else None
print(f"  No date filter              {r2.status_code:<8} {str(count2):<8} {str(total2):<8}")
if result2:
    p = result2[0]
    t = p.get("type", {})
    print(f"\n  Sample record (if any):")
    print(f"    customId:    {p.get('customId')}")
    print(f"    openedDate:  {p.get('openedDate')}")
    print(f"    type.value:  {t.get('value') if isinstance(t, dict) else t}")
    print(f"    type.text:   {t.get('text') if isinstance(t, dict) else ''}")
    print(f"    status:      {p.get('status', {}).get('value') if isinstance(p.get('status'), dict) else ''}")
