#!/usr/bin/env python3
"""
HCFL Data Quality Validation Script

Pulls a small sample of Hillsborough County HVAC permits from Accela's V4 API
and reports on data quality: field completeness, date filtering behavior,
enrichment data availability, and sample records (PII-redacted).

Does NOT require Supabase. Does NOT modify any remote state. Read-only.
"""
import os
import sys
import json
import requests
from collections import Counter
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
USERNAME = os.getenv("ACCELA_HCFL_USERNAME")
PASSWORD = os.getenv("ACCELA_HCFL_PASSWORD")
AGENCY = "HCFL"
ENVIRONMENT = "PROD"

AUTH_URL = "https://auth.accela.com/oauth2/token"
API_BASE = "https://apis.accela.com"

# 8-10 year-old permits from today (April 2026)
CURRENT_YEAR = datetime.now().year
DATE_FROM = f"{CURRENT_YEAR - 10}-01-01"
DATE_TO = f"{CURRENT_YEAR - 8}-12-31"

SAMPLE_SIZE = 25

def redact(s, show=3):
    """Redact PII for logging, keep first N chars for pattern detection."""
    if not s:
        return "(empty)"
    s = str(s)
    return s[:show] + "***" if len(s) > show else "***"

def auth():
    """Get access token via password grant."""
    print("[1/4] Authenticating against HCFL PROD...")
    r = requests.post(
        AUTH_URL,
        data={
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": USERNAME,
            "password": PASSWORD,
            "scope": "records",
            "agency_name": AGENCY,
            "environment": ENVIRONMENT,
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "x-accela-appid": CLIENT_ID,
        },
        timeout=30,
    )
    r.raise_for_status()
    token_data = r.json()
    print(f"      ✅ Got access token (expires in {token_data.get('expires_in', '?')}s)")
    return token_data["access_token"]

def search_permits_broad(access_token):
    """Sample 1: All Building permits (no type filter) to see type distribution."""
    print(f"\n[2/4] Sample 1: All Building permits {DATE_FROM} to {DATE_TO} (n={SAMPLE_SIZE})...")
    r = requests.post(
        f"{API_BASE}/v4/search/records",
        params={"limit": SAMPLE_SIZE, "offset": 0, "expand": "addresses,owners,parcels"},
        json={
            "module": "Building",
            "openedDateFrom": DATE_FROM,
            "openedDateTo": DATE_TO,
        },
        headers={
            "Authorization": access_token,
            "Content-Type": "application/json",
            "x-accela-appid": CLIENT_ID,
            "x-accela-agency": AGENCY,
        },
        timeout=30,
    )
    print(f"      HTTP {r.status_code} | Rate: {r.headers.get('x-ratelimit-remaining', '?')}/{r.headers.get('x-ratelimit-limit', '?')}")
    r.raise_for_status()
    return r.json().get("result", [])

def search_permits_hvac(access_token, permit_type):
    """Sample 2: Filtered to a specific HVAC permit type to see if API-level filtering works."""
    print(f"\n[3/4] Sample 2: Type-filtered '{permit_type}' (n={SAMPLE_SIZE})...")
    r = requests.post(
        f"{API_BASE}/v4/search/records",
        params={"limit": SAMPLE_SIZE, "offset": 0, "expand": "addresses,owners,parcels"},
        json={
            "module": "Building",
            "openedDateFrom": DATE_FROM,
            "openedDateTo": DATE_TO,
            "type": {"value": permit_type},
        },
        headers={
            "Authorization": access_token,
            "Content-Type": "application/json",
            "x-accela-appid": CLIENT_ID,
            "x-accela-agency": AGENCY,
        },
        timeout=30,
    )
    print(f"      HTTP {r.status_code} | Rate: {r.headers.get('x-ratelimit-remaining', '?')}/{r.headers.get('x-ratelimit-limit', '?')}")
    r.raise_for_status()
    return r.json().get("result", [])

def analyze(records, label):
    """Analyze data quality of returned permits."""
    print(f"\n    === {label.upper()} ANALYSIS ===")
    print(f"    Total records returned: {len(records)}")
    if not records:
        print("    (No data to analyze.)")
        return

    # Permit type distribution
    types = Counter()
    statuses = Counter()
    dates_seen = set()
    has_addresses = 0
    has_owners = 0
    has_parcels = 0
    has_jobvalue = 0
    permit_type_texts = Counter()

    for p in records:
        t = p.get("type", {})
        type_value = t.get("value") if isinstance(t, dict) else None
        type_text = t.get("text") if isinstance(t, dict) else None
        if type_value:
            types[type_value] += 1
        if type_text:
            permit_type_texts[type_text] += 1

        s = p.get("status", {})
        status_value = s.get("value") if isinstance(s, dict) else None
        if status_value:
            statuses[status_value] += 1

        opened = p.get("openedDate", "")
        if opened:
            dates_seen.add(opened[:10])

        if p.get("addresses"):
            has_addresses += 1
        if p.get("owners"):
            has_owners += 1
        if p.get("parcels"):
            has_parcels += 1
        if p.get("jobValue") or p.get("estimatedCost"):
            has_jobvalue += 1

    print(f"\n    Permit types found (type.value):")
    for t, c in types.most_common(10):
        print(f"      [{c:3d}] {t}")
    print(f"\n    Permit types found (type.text):")
    for t, c in permit_type_texts.most_common(10):
        print(f"      [{c:3d}] {t}")

    print(f"\n    Status distribution: {dict(statuses.most_common(5))}")

    # Date validation
    in_range = [d for d in dates_seen if DATE_FROM <= d <= DATE_TO]
    out_of_range = [d for d in dates_seen if not (DATE_FROM <= d <= DATE_TO)]
    print(f"\n    Date filtering:")
    print(f"      Dates in requested range ({DATE_FROM} to {DATE_TO}): {len(in_range)} unique")
    print(f"      Dates OUT of requested range: {len(out_of_range)} unique")
    if out_of_range:
        print(f"      ⚠️  Out-of-range dates (API ignored filter?): {sorted(out_of_range)[:5]}")
    print(f"      Earliest: {min(dates_seen) if dates_seen else 'N/A'}")
    print(f"      Latest:   {max(dates_seen) if dates_seen else 'N/A'}")

    # Enrichment completeness
    print(f"\n    Enrichment completeness (via expand parameter):")
    print(f"      Has addresses:  {has_addresses}/{len(records)} ({100*has_addresses/len(records):.0f}%)")
    print(f"      Has owners:     {has_owners}/{len(records)} ({100*has_owners/len(records):.0f}%)")
    print(f"      Has parcels:    {has_parcels}/{len(records)} ({100*has_parcels/len(records):.0f}%)")
    print(f"      Has jobValue:   {has_jobvalue}/{len(records)} ({100*has_jobvalue/len(records):.0f}%)")

    # Sample 2 records (PII-redacted)
    print(f"\n    Sample records (PII redacted):")
    for i, p in enumerate(records[:2]):
        print(f"\n      [{i+1}] customId: {p.get('customId', 'N/A')}  trackingId: {p.get('trackingId', 'N/A')}")
        print(f"          openedDate: {p.get('openedDate', 'N/A')}  statusDate: {p.get('statusDate', 'N/A')}")
        t = p.get("type", {})
        print(f"          type: value='{t.get('value') if isinstance(t, dict) else t}' text='{t.get('text') if isinstance(t, dict) else ''}'")
        print(f"          status: {p.get('status', {}).get('value') if isinstance(p.get('status'), dict) else p.get('status')}")
        print(f"          jobValue: {p.get('jobValue')}  estimatedCost: {p.get('estimatedCost')}")
        addrs = p.get("addresses") or []
        if addrs:
            a = addrs[0]
            print(f"          address[0]: {redact(a.get('streetNumberStart') or a.get('streetNo'), 99)} {redact(a.get('streetName'), 99)} {a.get('city','')} {a.get('state',{}).get('value','') if isinstance(a.get('state'), dict) else ''}")
        owners = p.get("owners") or []
        if owners:
            o = owners[0]
            print(f"          owner[0]: name={redact(o.get('fullName'), 5)}  city={o.get('city','')}")
        parcels = p.get("parcels") or []
        if parcels:
            par = parcels[0]
            print(f"          parcel[0]: parcelNumber={par.get('parcelNumber','N/A')} lotSize={par.get('lotSize','N/A')}")
        print(f"          raw field keys: {sorted(list(p.keys()))[:15]}")

def main():
    if not all([CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD]):
        print("❌ Missing env vars. Run from accela_oauth_probe/ directory with .env populated.")
        sys.exit(1)

    print("=" * 80)
    print(f"HILLSBOROUGH COUNTY (HCFL) ACCELA DATA QUALITY VALIDATION")
    print(f"Date range: {DATE_FROM} to {DATE_TO} (8-10 yr old permits, Signal A target)")
    print("=" * 80)

    token = auth()
    broad = search_permits_broad(token)
    analyze(broad, "BROAD: All Building permits")

    # Discover the right HVAC type name from broad results, then do a targeted search
    hvac_candidates = []
    for p in broad:
        t = p.get("type", {})
        tv = t.get("value") if isinstance(t, dict) else None
        tt = (t.get("text", "") or "").lower() if isinstance(t, dict) else ""
        if tv and any(kw in (tv + " " + tt).lower() for kw in ["mechanical", "hvac", "air", "ac ", "a/c"]):
            hvac_candidates.append(tv)

    if hvac_candidates:
        hvac_type = Counter(hvac_candidates).most_common(1)[0][0]
        print(f"\n[4/4] Detected HVAC-relevant type in sample: '{hvac_type}'")
        filtered = search_permits_hvac(token, hvac_type)
        analyze(filtered, f"FILTERED: type='{hvac_type}'")
    else:
        print(f"\n[4/4] No obvious HVAC type in broad sample — trying known HCFL type name...")
        # From CLAUDE.md + Citizen Access portal: HCFL uses "Residential Mechanical Trade Permit"
        filtered = search_permits_hvac(token, "Residential Mechanical Trade Permit")
        analyze(filtered, "FILTERED: type='Residential Mechanical Trade Permit'")

    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
