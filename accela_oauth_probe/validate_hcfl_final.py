#!/usr/bin/env python3
"""Final HCFL validation: corrected type format, recent date range, full field check."""
import os
import requests
from collections import Counter
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
USERNAME = os.getenv("ACCELA_HCFL_USERNAME")
PASSWORD = os.getenv("ACCELA_HCFL_PASSWORD")

r = requests.post(
    "https://auth.accela.com/oauth2/token",
    data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
          "username": USERNAME, "password": PASSWORD, "scope": "records",
          "agency_name": "HCFL", "environment": "PROD"},
    headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
    timeout=30)
r.raise_for_status()
token = r.json()["access_token"]

headers = {"Authorization": token, "Content-Type": "application/json",
           "x-accela-appid": CLIENT_ID, "x-accela-agency": "HCFL"}

# Step 1: Pull 100 recent Building permits (no type filter) to see what types exist
print("=" * 80)
print("STEP 1: Permit type distribution in HCFL 2024-2025 (sample 100)")
print("=" * 80)
r = requests.post(
    "https://apis.accela.com/v4/search/records",
    params={"limit": 100, "offset": 0},
    json={"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2025-12-31"},
    headers=headers, timeout=60)
recs = r.json().get("result", [])
print(f"Returned: {len(recs)} permits\n")

type_counter = Counter()
hvac_keywords = ["mechanical", "hvac", "air", "a/c", "ac ", "cool", "heat", "furnace"]
hvac_types = Counter()
for p in recs:
    t = p.get("type", {})
    tv = t.get("value") if isinstance(t, dict) else None
    tt = (t.get("text", "") or "") if isinstance(t, dict) else ""
    if tv:
        type_counter[tv] += 1
        combined = (tv + " " + tt).lower()
        if any(kw in combined for kw in hvac_keywords):
            hvac_types[tv] += 1

print("Top 15 permit types (hierarchical value):")
for t, c in type_counter.most_common(15):
    print(f"  [{c:3d}] {t}")

print(f"\nHVAC-related types found:")
for t, c in hvac_types.most_common():
    print(f"  [{c:3d}] {t}")

# Step 2: Use the discovered HVAC type(s) to do targeted queries
print("\n" + "=" * 80)
print("STEP 2: Targeted HVAC search with CORRECT hierarchical type format")
print("=" * 80)

candidates_to_try = list(hvac_types.keys()) + [
    "Building/Residential/Trade/Mechanical",  # from CLAUDE.md
    "Building/Commercial/Trade/Mechanical",
    "Building/Residential/Mechanical/NA",
]
seen = set()
candidates_to_try = [c for c in candidates_to_try if not (c in seen or seen.add(c))]

for ptype in candidates_to_try:
    try:
        r = requests.post(
            "https://apis.accela.com/v4/search/records",
            params={"limit": 5, "offset": 0, "expand": "addresses,owners,parcels"},
            json={"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2025-12-31",
                  "type": {"value": ptype}},
            headers=headers, timeout=30)
        results = r.json().get("result", []) if r.status_code == 200 else []
        print(f"\n  type='{ptype}': {len(results)} records")
        if results:
            # Check enrichment
            has_addr = sum(1 for p in results if p.get("addresses"))
            has_own = sum(1 for p in results if p.get("owners"))
            has_par = sum(1 for p in results if p.get("parcels"))
            print(f"    enrichment: addresses={has_addr}/5, owners={has_own}/5, parcels={has_par}/5")
            # Show one sample
            p = results[0]
            print(f"    sample: customId={p.get('customId')} opened={p.get('openedDate', '')[:10]} "
                  f"jobValue={p.get('jobValue')} status={p.get('status', {}).get('value') if isinstance(p.get('status'), dict) else ''}")
            addrs = p.get("addresses") or []
            if addrs:
                a = addrs[0]
                # show only redacted street address
                sn = (a.get('streetNumberStart') or a.get('streetNo') or '')
                print(f"    address keys: {sorted(list(a.keys()))[:10]}")
                print(f"    streetNumber populated: {'YES' if sn else 'NO'}, city: {a.get('city')}, zip: {a.get('postalCode') or a.get('zip')}")
            owners = p.get("owners") or []
            if owners:
                o = owners[0]
                print(f"    owner keys: {sorted(list(o.keys()))[:10]}")
                print(f"    owner name populated: {'YES' if o.get('fullName') else 'NO'}")
            parcels = p.get("parcels") or []
            if parcels:
                par = parcels[0]
                print(f"    parcel keys: {sorted(list(par.keys()))[:10]}")
                print(f"    parcel number: {par.get('parcelNumber', 'N/A')}")
    except Exception as e:
        print(f"\n  type='{ptype}': ERROR {e}")

# Step 3: Pull a bigger sample of mechanical permits and analyze aggregate quality
print("\n" + "=" * 80)
print("STEP 3: Aggregate quality on 50 residential mechanical permits (2024-2025)")
print("=" * 80)
hvac_type_use = candidates_to_try[0] if candidates_to_try else "Building/Residential/Trade/Mechanical"
r = requests.post(
    "https://apis.accela.com/v4/search/records",
    params={"limit": 50, "offset": 0, "expand": "addresses,owners,parcels"},
    json={"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2025-12-31",
          "type": {"value": hvac_type_use}},
    headers=headers, timeout=60)
big = r.json().get("result", [])
print(f"Pulling type='{hvac_type_use}': got {len(big)} records\n")

if big:
    fields_present = Counter()
    for p in big:
        for k, v in p.items():
            if v is not None and v != "" and v != [] and v != {}:
                fields_present[k] += 1

    print(f"Field completeness (top 25 of {len(fields_present)} fields):")
    for f, c in sorted(fields_present.items(), key=lambda x: -x[1])[:25]:
        pct = 100 * c / len(big)
        print(f"  {f:<30} {c:>3}/{len(big)} ({pct:>5.1f}%)")

    # Specific critical fields for lead gen
    critical = ["customId", "openedDate", "type", "status", "jobValue", "estimatedCost",
                "description", "addresses", "owners", "parcels"]
    print(f"\nCritical fields for HVAC lead gen:")
    for f in critical:
        c = fields_present.get(f, 0)
        pct = 100 * c / len(big)
        marker = "✅" if pct >= 80 else ("⚠️ " if pct >= 40 else "❌")
        print(f"  {marker} {f:<20} {c}/{len(big)} ({pct:.0f}%)")
