#!/usr/bin/env python3
"""
Authorization-Code-flow test against PINELLAS.

Hypothesis: Password grant tokens are not properly scoped to an agency's ACA
session, causing 500s on data queries. Authorization code flow (going through
Accela's ACA redirect + consent) produces a properly-scoped refresh_token
that should unlock data queries.

Usage:
    python test_authcode_pinellas.py <AUTH_CODE>

The AUTH_CODE is captured from the redirect URL after the user consents
in Chrome on https://auth.accela.com/oauth2/authorize?... (URL generated
separately by the workflow).
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
REDIRECT_URI = "https://hvac-backend-production-11e6.up.railway.app/api/counties/oauth/callback"

if len(sys.argv) < 2:
    print("ERROR: pass the authorization code as argv[1]")
    sys.exit(1)
code = sys.argv[1]

print("=" * 80)
print("AUTHORIZATION CODE FLOW TEST — PINELLAS")
print("=" * 80)
print(f"Code length: {len(code)}")

# STEP 1: Exchange the code for tokens
print("\n[1/3] Exchanging authorization code for tokens...")
r = requests.post(
    "https://auth.accela.com/oauth2/token",
    data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    },
    headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "x-accela-appid": CLIENT_ID,
    },
    timeout=30,
)
print(f"  HTTP {r.status_code}")
if r.status_code != 200:
    print(f"  BODY: {r.text[:500]}")
    sys.exit(2)

tok = r.json()
access_token = tok["access_token"]
refresh_token = tok.get("refresh_token", "")
expires_in = tok.get("expires_in", "?")
scope = tok.get("scope", "?")
print(f"  ✅ Got access_token (expires in {expires_in}s, scope='{scope}')")
print(f"  ✅ Got refresh_token (length: {len(refresh_token)})")

# STEP 2: Query records for PINELLAS using the fresh authcode-flow token
print("\n[2/3] Querying POST /v4/search/records for PINELLAS (2024-2025 Building permits)...")
r2 = requests.post(
    "https://apis.accela.com/v4/search/records",
    params={"limit": 10, "offset": 0, "expand": "addresses,owners,parcels"},
    json={
        "module": "Building",
        "openedDateFrom": "2024-01-01",
        "openedDateTo": "2025-12-31",
    },
    headers={
        "Authorization": access_token,
        "Content-Type": "application/json",
        "x-accela-appid": CLIENT_ID,
        "x-accela-agency": "PINELLAS",
    },
    timeout=30,
)
print(f"  HTTP {r2.status_code}")
print(f"  Rate: {r2.headers.get('x-ratelimit-remaining','?')}/{r2.headers.get('x-ratelimit-limit','?')}")

if r2.status_code == 200:
    recs = r2.json().get("result", []) or []
    print(f"  ✅✅✅ SUCCESS — got {len(recs)} records")
    if recs:
        p = recs[0]
        t = p.get("type", {})
        print(f"\n  Sample record:")
        print(f"    customId:      {p.get('customId')}")
        print(f"    type.value:    {t.get('value') if isinstance(t, dict) else t}")
        print(f"    type.text:     {t.get('text') if isinstance(t, dict) else ''}")
        print(f"    openedDate:    {p.get('openedDate','')[:10]}")
        print(f"    status:        {p.get('status', {}).get('value') if isinstance(p.get('status'), dict) else p.get('status')}")
        has_addr = sum(1 for rr in recs if rr.get("addresses"))
        has_own = sum(1 for rr in recs if rr.get("owners"))
        has_par = sum(1 for rr in recs if rr.get("parcels"))
        print(f"\n  Enrichment (over {len(recs)} records):")
        print(f"    addresses: {has_addr}/{len(recs)}")
        print(f"    owners:    {has_own}/{len(recs)}")
        print(f"    parcels:   {has_par}/{len(recs)}")

    # STEP 3: Also test an HVAC-type filter
    print("\n[3/3] Type-filtered query for HVAC permits (Building/Residential/Trade/Mechanical)...")
    for ptype in ["Building/Residential/Trade/Mechanical", "Building/Commercial/Trade/Mechanical", "Residential Mechanical"]:
        r3 = requests.post(
            "https://apis.accela.com/v4/search/records",
            params={"limit": 3, "offset": 0, "expand": "addresses,owners,parcels"},
            json={
                "module": "Building",
                "openedDateFrom": "2024-01-01",
                "openedDateTo": "2025-12-31",
                "type": {"value": ptype},
            },
            headers={
                "Authorization": access_token,
                "Content-Type": "application/json",
                "x-accela-appid": CLIENT_ID,
                "x-accela-agency": "PINELLAS",
            },
            timeout=30,
        )
        if r3.status_code == 200:
            n = len(r3.json().get("result", []) or [])
            print(f"  type='{ptype}': HTTP {r3.status_code}, count={n}")
        else:
            print(f"  type='{ptype}': HTTP {r3.status_code}, body={r3.text[:100]}")
else:
    print(f"  ❌ body: {r2.text[:500]}")

# Save the tokens to disk for reuse (local only, gitignored)
out = {
    "agency": "PINELLAS",
    "environment": "PROD",
    "access_token_len": len(access_token),
    "refresh_token_len": len(refresh_token),
    "scope": scope,
    "expires_in": expires_in,
}
with open("pinellas_tokens_summary.json", "w") as f:
    json.dump(out, f, indent=2)

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
