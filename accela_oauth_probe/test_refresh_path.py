#!/usr/bin/env python3
"""Test the EXACT production code path: authcode → exchange → store refresh_token →
refresh_access_token (grant_type=refresh_token) → records query with REFRESHED token.

Hypothesis: the token produced by grant_type=refresh_token is differently-scoped
than the token from the initial authcode exchange, and that's what unlocks 500s."""
import os, sys, json, requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
REDIRECT_URI = "https://hvac-backend-production-11e6.up.railway.app/api/counties/oauth/callback"

code = sys.argv[1]

def test_records(access_token, label):
    r = requests.post(
        "https://apis.accela.com/v4/search/records",
        params={"limit": 3, "expand": "addresses,owners,parcels"},
        json={"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2024-12-31"},
        headers={"Authorization": access_token, "Content-Type": "application/json",
                 "x-accela-appid": CLIENT_ID, "x-accela-agency": "PINELLAS"},
        timeout=30,
    )
    try:
        j = r.json()
        n = len(j.get("result") or []) if j.get("result") else 0
        err = j.get("code") if r.status_code != 200 else None
    except:
        n, err = "?", "parse_err"
    icon = "✅" if r.status_code == 200 and isinstance(n, int) and n > 0 else "❌"
    print(f"  {icon} [{label}] HTTP {r.status_code} | n={n} | err={err} | trace={(r.json() or {}).get('traceId','')[:25] if r.text else ''}")
    return r.status_code, r.json() if r.status_code == 200 else None

# STEP 1: Exchange auth code for initial tokens
print("=" * 80)
print("STEP 1: Exchange authorization code → initial tokens")
print("=" * 80)
r = requests.post("https://auth.accela.com/oauth2/token",
    data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
          "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
    headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
    timeout=30)
if r.status_code != 200:
    print(f"❌ Code exchange failed: {r.status_code} {r.text[:200]}")
    sys.exit(2)
initial = r.json()
print(f"✅ Initial token obtained")
print(f"   scope: {initial.get('scope')}")
print(f"   expires_in: {initial.get('expires_in')}s")
print(f"   access_token length: {len(initial['access_token'])}")
print(f"   refresh_token length: {len(initial.get('refresh_token',''))}")

# STEP 2: Test records with initial token (we know this 500s)
print("\n" + "=" * 80)
print("STEP 2: Records query with INITIAL authcode-flow access_token (we expect 500)")
print("=" * 80)
test_records(initial["access_token"], "INITIAL authcode token")

# STEP 3: Exchange refresh_token → new access_token (what production does)
print("\n" + "=" * 80)
print("STEP 3: Exchange refresh_token → NEW access_token (production path)")
print("=" * 80)
r = requests.post("https://auth.accela.com/oauth2/token",
    data={"grant_type": "refresh_token", "refresh_token": initial["refresh_token"],
          "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
    headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
    timeout=30)
if r.status_code != 200:
    print(f"❌ Refresh failed: {r.status_code} {r.text[:300]}")
    sys.exit(3)
refreshed = r.json()
print(f"✅ Refreshed token obtained")
print(f"   scope: {refreshed.get('scope')}")
print(f"   expires_in: {refreshed.get('expires_in')}s")
print(f"   access_token length: {len(refreshed['access_token'])}")
print(f"   Same as initial? {'YES' if refreshed['access_token'] == initial['access_token'] else 'NO (different token)'}")

# STEP 4: Test records with REFRESHED token (the real production path test)
print("\n" + "=" * 80)
print("STEP 4: Records query with REFRESHED access_token (the production path)")
print("=" * 80)
status, body = test_records(refreshed["access_token"], "REFRESHED token")

# STEP 5: Also try second refresh (chain)
print("\n" + "=" * 80)
print("STEP 5: Second refresh (some systems only issue good tokens after chain)")
print("=" * 80)
r = requests.post("https://auth.accela.com/oauth2/token",
    data={"grant_type": "refresh_token", "refresh_token": refreshed.get("refresh_token", initial["refresh_token"]),
          "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
    headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
    timeout=30)
if r.status_code == 200:
    refreshed2 = r.json()
    print(f"✅ Second refresh succeeded (length: {len(refreshed2['access_token'])})")
    test_records(refreshed2["access_token"], "DOUBLE-REFRESHED token")
else:
    print(f"❌ Second refresh failed: {r.status_code} {r.text[:200]}")

# SAMPLE DATA if we got success anywhere
if status == 200 and body:
    recs = body.get("result") or []
    if recs:
        print("\n" + "=" * 80)
        print("🎉 SAMPLE RECORD FROM SUCCESSFUL QUERY")
        print("=" * 80)
        p = recs[0]
        t = p.get("type", {})
        print(f"  customId:   {p.get('customId')}")
        print(f"  openedDate: {p.get('openedDate','')[:10]}")
        print(f"  type:       {t.get('value') if isinstance(t, dict) else t}")
        print(f"  status:     {p.get('status', {}).get('value') if isinstance(p.get('status'), dict) else ''}")
        print(f"  addresses: {len(p.get('addresses') or [])}, owners: {len(p.get('owners') or [])}, parcels: {len(p.get('parcels') or [])}")

print("\n" + "=" * 80)
print("DONE")
