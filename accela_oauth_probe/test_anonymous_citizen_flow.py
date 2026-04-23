#!/usr/bin/env python3
"""
BREAKTHROUGH TEST: Per Accela docs, POST /v4/search/records for citizen apps
has "Authorization Type: No authorization required". Token is OPTIONAL.
Try WITHOUT Authorization header — just x-accela-appid + x-accela-agency
+ x-accela-environment.

Test against the agencies we've confirmed fail (PINELLAS, LEECO, etc.) and
the one that works (HCFL) as a control.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")

TEST_AGENCIES = ["HCFL", "PINELLAS", "LEECO", "LEONCO", "MARTINCO", "PASCO", "POLKCO", "BOCC"]

def test_anonymous(agency):
    """No Authorization header — just the 3 citizen-app headers."""
    r = requests.post(
        "https://apis.accela.com/v4/search/records",
        params={"limit": 5, "offset": 0, "expand": "addresses,owners,parcels"},
        json={"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2025-12-31"},
        headers={
            "Content-Type": "application/json",
            "x-accela-appid": CLIENT_ID,
            "x-accela-agency": agency,
            "x-accela-environment": "PROD",
        },
        timeout=30,
    )
    return r

print("=" * 90)
print("BREAKTHROUGH TEST — Anonymous Citizen App flow (no Authorization header)")
print("=" * 90)
print(f"{'Agency':<10} {'Status':<8} {'Count':<8} Notes")
print("-" * 90)

for agency in TEST_AGENCIES:
    try:
        r = test_anonymous(agency)
        status = r.status_code
        try:
            body = r.json()
            result = body.get("result") or []
            count = len(result) if isinstance(result, list) else "?"
            err = body.get("code") if status != 200 else None
            trace = body.get("traceId", "")[:25] if status != 200 else ""
            notes = f"{err} {trace}" if err else "SUCCESS"
        except Exception:
            count = "?"
            notes = r.text[:60]
        icon = "✅" if status == 200 and isinstance(count, int) and count > 0 else ("⚪" if status == 200 else "❌")
        print(f"{icon} {agency:<8} {status:<8} {str(count):<8} {notes}")
        # If success, show a sample record
        if status == 200 and isinstance(count, int) and count > 0:
            p = body["result"][0]
            t = p.get("type", {})
            print(f"       Sample: customId={p.get('customId')} | type={t.get('value') if isinstance(t, dict) else t} | opened={p.get('openedDate','')[:10]}")
    except Exception as e:
        print(f"   {agency:<8} EXCEPTION: {e}")
