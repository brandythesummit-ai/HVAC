#!/usr/bin/env python3
"""Test Pinellas API with additional headers we may have been missing, notably x-accela-environment."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
USERNAME = os.getenv("ACCELA_HCFL_USERNAME")
PASSWORD = os.getenv("ACCELA_HCFL_PASSWORD")

def auth(agency):
    r = requests.post("https://auth.accela.com/oauth2/token",
        data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
              "username": USERNAME, "password": PASSWORD, "scope": "records",
              "agency_name": agency, "environment": "PROD"},
        headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
        timeout=30)
    return r.json()["access_token"] if r.status_code == 200 else None

tok_pin = auth("PINELLAS")
tok_hcfl = auth("HCFL")

# Header variations to try for PINELLAS
header_variants = [
    ("Baseline (what I was using)", {
        "Authorization": tok_pin,
        "Content-Type": "application/json",
        "x-accela-appid": CLIENT_ID,
        "x-accela-agency": "PINELLAS",
    }),
    ("+ x-accela-environment: PROD", {
        "Authorization": tok_pin,
        "Content-Type": "application/json",
        "x-accela-appid": CLIENT_ID,
        "x-accela-agency": "PINELLAS",
        "x-accela-environment": "PROD",
    }),
    ("+ x-accela-appsecret (citizen app auth)", {
        "Authorization": tok_pin,
        "Content-Type": "application/json",
        "x-accela-appid": CLIENT_ID,
        "x-accela-appsecret": CLIENT_SECRET,
        "x-accela-agency": "PINELLAS",
        "x-accela-environment": "PROD",
    }),
    ("Bearer-prefixed Authorization", {
        "Authorization": f"Bearer {tok_pin}",
        "Content-Type": "application/json",
        "x-accela-appid": CLIENT_ID,
        "x-accela-agency": "PINELLAS",
        "x-accela-environment": "PROD",
    }),
    ("All known headers combined", {
        "Authorization": tok_pin,
        "Content-Type": "application/json",
        "x-accela-appid": CLIENT_ID,
        "x-accela-appsecret": CLIENT_SECRET,
        "x-accela-agency": "PINELLAS",
        "x-accela-environment": "PROD",
        "Accept": "application/json",
    }),
]

print("=" * 80)
print("PINELLAS — Testing header variants on POST /v4/search/records")
print("=" * 80)

body = {"module": "Building", "openedDateFrom": "2025-01-01", "openedDateTo": "2025-12-31"}
params = {"limit": 3, "offset": 0}

for label, hdrs in header_variants:
    r = requests.post("https://apis.accela.com/v4/search/records",
                      params=params, json=body, headers=hdrs, timeout=30)
    count = "?"
    try:
        data = r.json()
        results = data.get("result") or []
        count = len(results) if isinstance(results, list) else "?"
        if r.status_code != 200:
            body_preview = r.text[:200].replace('\n', ' ')
        else:
            body_preview = f"{count} records"
    except Exception:
        body_preview = r.text[:200]
    print(f"\n  [{label}]")
    print(f"    HTTP {r.status_code}")
    print(f"    {body_preview}")

# Do the SAME test for HCFL so we have a clean "what works for HCFL" comparison
print("\n\n" + "=" * 80)
print("HCFL — Same header variants (control)")
print("=" * 80)

# Swap tokens and agency
hcfl_variants = [(label, dict(h, **{"Authorization": tok_hcfl if "Bearer" not in str(h.get("Authorization","")) else f"Bearer {tok_hcfl}", "x-accela-agency": "HCFL"}))
                 for label, h in header_variants]

for label, hdrs in hcfl_variants:
    r = requests.post("https://apis.accela.com/v4/search/records",
                      params=params, json=body, headers=hdrs, timeout=30)
    try:
        data = r.json()
        results = data.get("result") or []
        count = len(results) if isinstance(results, list) else "?"
        if r.status_code != 200:
            body_preview = r.text[:200].replace('\n', ' ')
        else:
            body_preview = f"{count} records"
    except Exception:
        body_preview = r.text[:200]
    print(f"  [{label}] HTTP {r.status_code} — {body_preview}")

# Also: try the Pinellas portal's LIKELY V4 citizen endpoint (different base URL)
print("\n\n" + "=" * 80)
print("ALTERNATIVE BASE URL — try aca-prod.accela.com/PINELLAS API paths directly")
print("=" * 80)
# Accela Citizen Access portals sometimes expose /apiservices/ or /api/ paths
for path in ["https://aca-prod.accela.com/PINELLAS/apiservices/v4/search/records",
             "https://aca-prod.accela.com/PINELLAS/api/v4/search/records"]:
    try:
        r = requests.post(path,
                          params=params, json=body,
                          headers={
                              "Authorization": tok_pin,
                              "Content-Type": "application/json",
                              "x-accela-appid": CLIENT_ID,
                              "x-accela-agency": "PINELLAS",
                              "x-accela-environment": "PROD",
                          },
                          timeout=15)
        print(f"  {path}: HTTP {r.status_code} {r.text[:100]}")
    except Exception as e:
        print(f"  {path}: {type(e).__name__}: {e}")
