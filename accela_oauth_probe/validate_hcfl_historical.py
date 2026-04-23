#!/usr/bin/env python3
"""Confirm that HCFL HVAC permits from 2016-2018 are retrievable via completedDate filter."""
import os
import requests
from collections import Counter
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
USERNAME = os.getenv("ACCELA_HCFL_USERNAME")
PASSWORD = os.getenv("ACCELA_HCFL_PASSWORD")

r = requests.post("https://auth.accela.com/oauth2/token",
    data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
          "username": USERNAME, "password": PASSWORD, "scope": "records",
          "agency_name": "HCFL", "environment": "PROD"},
    headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
    timeout=30)
r.raise_for_status()
token = r.json()["access_token"]
headers = {"Authorization": token, "Content-Type": "application/json",
           "x-accela-appid": CLIENT_ID, "x-accela-agency": "HCFL"}

print("=" * 80)
print("SIGNAL A VALIDATION: Residential Mechanical permits COMPLETED 2016-2018")
print("(using completedDateFrom/To filter, the workaround for the openedDate cutoff)")
print("=" * 80)

# Pull 50 residential mechanical permits COMPLETED in 2016-2018
r = requests.post(
    "https://apis.accela.com/v4/search/records",
    params={"limit": 50, "offset": 0, "expand": "addresses,owners,parcels"},
    json={
        "module": "Building",
        "completedDateFrom": "2016-01-01",
        "completedDateTo": "2018-12-31",
        "type": {"value": "Building/Residential/Trade/Mechanical"},
    },
    headers=headers, timeout=60)

print(f"\nHTTP {r.status_code}")
data = r.json()
records = data.get("result", [])
print(f"Records returned: {len(records)}\n")

if not records:
    print("⚠️  Empty result — the completedDate workaround didn't work for residential mechanical either.")
    # Try without type filter
    r2 = requests.post(
        "https://apis.accela.com/v4/search/records",
        params={"limit": 5, "offset": 0},
        json={"module": "Building", "completedDateFrom": "2017-01-01", "completedDateTo": "2017-12-31"},
        headers=headers, timeout=30)
    d2 = r2.json()
    rc2 = d2.get("result", [])
    print(f"\nControl: all Building completed in 2017 → {len(rc2)} records")
    if rc2:
        print("Sample types found:")
        for p in rc2:
            t = p.get("type", {})
            print(f"  {t.get('value')} | opened={p.get('openedDate','')[:10]} completed={p.get('completedDate','')[:10]}")
else:
    # Analyze the older data
    opened_years = Counter()
    completed_years = Counter()
    types = Counter()
    has_addr = has_own = has_par = 0

    for p in records:
        od = p.get("openedDate", "")
        cd = p.get("completedDate", "")
        if od: opened_years[od[:4]] += 1
        if cd: completed_years[cd[:4]] += 1
        t = p.get("type", {})
        if t: types[t.get("value", "?")] += 1
        if p.get("addresses"): has_addr += 1
        if p.get("owners"): has_own += 1
        if p.get("parcels"): has_par += 1

    print("openedDate year distribution:")
    for y, c in sorted(opened_years.items()):
        print(f"  {y}: {c}")
    print("\ncompletedDate year distribution:")
    for y, c in sorted(completed_years.items()):
        print(f"  {y}: {c}")
    print(f"\nType distribution: {dict(types)}")
    print(f"\nEnrichment:")
    print(f"  addresses: {has_addr}/{len(records)} ({100*has_addr/len(records):.0f}%)")
    print(f"  owners:    {has_own}/{len(records)} ({100*has_own/len(records):.0f}%)")
    print(f"  parcels:   {has_par}/{len(records)} ({100*has_par/len(records):.0f}%)")

    print(f"\nFirst 3 records (sample):")
    for i, p in enumerate(records[:3]):
        t = p.get("type", {})
        s = p.get("status", {})
        print(f"\n  [{i+1}] customId: {p.get('customId')}")
        print(f"      type.value: {t.get('value') if isinstance(t, dict) else t}")
        print(f"      opened: {p.get('openedDate','')[:10]}  completed: {p.get('completedDate','')[:10]}")
        print(f"      status: {s.get('value') if isinstance(s, dict) else s}")
        print(f"      jobValue: {p.get('jobValue')}")
        print(f"      description: {(p.get('description','') or '')[:80]}")
        addrs = p.get("addresses") or []
        if addrs:
            a = addrs[0]
            print(f"      address: {a.get('addressLine1', '(none)')[:50]} {a.get('city','')} {a.get('postalCode','')}")
        owners = p.get("owners") or []
        if owners:
            o = owners[0]
            fn = o.get('fullName','')
            print(f"      owner: {fn[:3] + '***' if fn else '(none)'}")
