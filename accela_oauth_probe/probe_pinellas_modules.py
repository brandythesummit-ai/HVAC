#!/usr/bin/env python3
"""Test Pinellas with its ACTUAL module names (visible in their ACA dashboard)."""
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
          "agency_name": "PINELLAS", "environment": "PROD"},
    headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
    timeout=30)
r.raise_for_status()
token = r.json()["access_token"]
print(f"✅ Token obtained")

headers = {"Authorization": token, "Content-Type": "application/json",
           "x-accela-appid": CLIENT_ID, "x-accela-agency": "PINELLAS"}

# Real Pinellas modules (from their ACA portal dashboard)
modules_to_test = [
    "Build", "Develop", "Plan", "PCCLB", "Utilities",
    "Water/Nav", "Emergency Mgmt", "Fertilizer",
    "Air Quality", "Environment", "Human Services",
    "Building",   # control — known to 500
    "DRS",        # control — known to 500
]

print("\n" + "=" * 80)
print("PINELLAS MODULE TEST — which modules actually return data?")
print("=" * 80)

working = []
for m in modules_to_test:
    r = requests.post(
        "https://apis.accela.com/v4/search/records",
        params={"limit": 5},
        json={"module": m, "openedDateFrom": "2025-01-01", "openedDateTo": "2025-12-31"},
        headers=headers, timeout=30)
    try:
        body = r.json()
        results = body.get("result") or []
        count = len(results) if isinstance(results, list) else "?"
    except Exception:
        count = "?"
        body = {"raw": r.text[:100]}
    status = r.status_code
    if status == 200 and isinstance(count, int) and count > 0:
        working.append((m, count))
        # Show a sample record
        sample = results[0]
        t = sample.get("type", {})
        print(f"\n  ✅ module='{m}': {count} records")
        print(f"       Sample: customId={sample.get('customId')}")
        print(f"               type.value={t.get('value') if isinstance(t, dict) else t}")
        print(f"               type.text={t.get('text') if isinstance(t, dict) else ''}")
        print(f"               openedDate={sample.get('openedDate','')[:10]}")
    elif status == 200:
        print(f"  ⚪ module='{m}': {count} records (empty)")
    else:
        print(f"  ❌ module='{m}': HTTP {status}")

print(f"\n\nWorking modules: {[w[0] for w in working]}")

# If anything worked, dig deeper into it to find HVAC-related types
if working:
    best_module = working[0][0]
    print(f"\n" + "=" * 80)
    print(f"TYPE DISTRIBUTION for module='{best_module}' (sample up to 200)")
    print("=" * 80)
    r = requests.post(
        "https://apis.accela.com/v4/search/records",
        params={"limit": 200},
        json={"module": best_module, "openedDateFrom": "2024-01-01", "openedDateTo": "2025-12-31"},
        headers=headers, timeout=60)
    recs = r.json().get("result", []) or []
    print(f"Got {len(recs)} records")
    types = Counter()
    hvac_types = Counter()
    hvac_keywords = ["mechanical", "hvac", "air cond", "a/c", "ac ", "cool", "heat"]
    for p in recs:
        t = p.get("type", {})
        tv = t.get("value") if isinstance(t, dict) else None
        tt = (t.get("text") or "") if isinstance(t, dict) else ""
        if tv:
            types[tv] += 1
            combined = (tv + " " + tt).lower()
            if any(kw in combined for kw in hvac_keywords):
                hvac_types[tv] += 1

    print(f"\nTop 20 permit types:")
    for t, c in types.most_common(20):
        print(f"  [{c:3d}] {t}")
    print(f"\n🔥 HVAC-related:")
    for t, c in hvac_types.most_common():
        print(f"  [{c:3d}] {t}")
