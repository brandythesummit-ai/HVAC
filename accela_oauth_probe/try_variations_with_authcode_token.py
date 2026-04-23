#!/usr/bin/env python3
"""Given a fresh authcode-flow access_token (scope: records), try EVERY
documented request variation to find one that bypasses the 500."""
import os, sys, requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
REDIRECT_URI = "https://hvac-backend-production-11e6.up.railway.app/api/counties/oauth/callback"

code = sys.argv[1]

# Exchange code → token
r = requests.post("https://auth.accela.com/oauth2/token",
    data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
          "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
    headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
    timeout=30)
if r.status_code != 200:
    print(f"Token exchange failed: {r.status_code} {r.text[:200]}")
    sys.exit(2)
token = r.json()["access_token"]
refresh = r.json().get("refresh_token")
print(f"✅ Token obtained (scope: {r.json().get('scope')}, expires: {r.json().get('expires_in')}s)")

# Try every request variation
variations = [
    ("Baseline (our current)", "POST", "/v4/search/records",
     {"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2024-12-31"},
     {"Authorization": token, "Content-Type": "application/json",
      "x-accela-appid": CLIENT_ID, "x-accela-agency": "PINELLAS"},
     {"limit": 3}),
    ("WITHOUT x-accela-agency header", "POST", "/v4/search/records",
     {"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2024-12-31"},
     {"Authorization": token, "Content-Type": "application/json",
      "x-accela-appid": CLIENT_ID},
     {"limit": 3}),
    ("With x-accela-environment: PROD", "POST", "/v4/search/records",
     {"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2024-12-31"},
     {"Authorization": token, "Content-Type": "application/json",
      "x-accela-appid": CLIENT_ID, "x-accela-agency": "PINELLAS",
      "x-accela-environment": "PROD"},
     {"limit": 3}),
    ("GET /v4/records (different endpoint)", "GET", "/v4/records",
     None,
     {"Authorization": token, "x-accela-appid": CLIENT_ID,
      "x-accela-agency": "PINELLAS"},
     {"limit": 3, "module": "Building",
      "openedDateFrom": "2024-01-01", "openedDateTo": "2024-12-31"}),
    ("GET /v4/records WITHOUT x-accela-agency", "GET", "/v4/records",
     None,
     {"Authorization": token, "x-accela-appid": CLIENT_ID},
     {"limit": 3, "module": "Building",
      "openedDateFrom": "2024-01-01", "openedDateTo": "2024-12-31"}),
    ("Minimal body — no module", "POST", "/v4/search/records",
     {"openedDateFrom": "2024-01-01", "openedDateTo": "2024-12-31"},
     {"Authorization": token, "Content-Type": "application/json",
      "x-accela-appid": CLIENT_ID, "x-accela-agency": "PINELLAS"},
     {"limit": 3}),
    ("GET /v4/search/records (GET instead of POST)", "GET", "/v4/search/records",
     None,
     {"Authorization": token, "x-accela-appid": CLIENT_ID,
      "x-accela-agency": "PINELLAS"},
     {"limit": 3, "module": "Building"}),
    ("With x-accela-appsecret header", "POST", "/v4/search/records",
     {"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2024-12-31"},
     {"Authorization": token, "Content-Type": "application/json",
      "x-accela-appid": CLIENT_ID, "x-accela-appsecret": CLIENT_SECRET,
      "x-accela-agency": "PINELLAS"},
     {"limit": 3}),
    ("With explicit agency_name + environment in body", "POST", "/v4/search/records",
     {"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2024-12-31",
      "agency_name": "PINELLAS", "environment": "PROD"},
     {"Authorization": token, "Content-Type": "application/json",
      "x-accela-appid": CLIENT_ID, "x-accela-agency": "PINELLAS"},
     {"limit": 3}),
    ("Different path — /v4/records/byId", "GET", "/v4/records/byId",
     None,
     {"Authorization": token, "x-accela-appid": CLIENT_ID,
      "x-accela-agency": "PINELLAS"},
     {}),
    # Try a non-records endpoint with fresh token
    ("GET /v4/agencies/PINELLAS/recordTypes with records scope token", "GET", "/v4/agencies/PINELLAS/recordTypes",
     None,
     {"Authorization": token, "x-accela-appid": CLIENT_ID},
     {"module": "Building", "limit": 5}),
]

print(f"\n{'='*100}")
for label, method, path, body, headers, params in variations:
    url = f"https://apis.accela.com{path}"
    if method == "POST":
        r = requests.post(url, params=params, json=body, headers=headers, timeout=30)
    else:
        r = requests.get(url, params=params, headers=headers, timeout=30)
    try:
        j = r.json()
        result = j.get("result")
        n = len(result) if isinstance(result, list) else "?"
        err = j.get("code") if r.status_code != 200 else None
        more = (j.get("more") or "")[:50]
    except:
        n = "?"
        err = "parse_err"
        more = r.text[:80]
    status_icon = "✅" if r.status_code == 200 and isinstance(n, int) and n > 0 else ("⚪" if r.status_code == 200 else "❌")
    print(f"{status_icon} HTTP {r.status_code} | n={n} | err={err} | {label}")
    if r.status_code != 200 and err:
        print(f"   more: {more}")
