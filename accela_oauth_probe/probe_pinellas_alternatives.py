#!/usr/bin/env python3
"""Test alternative V4 endpoints that may bypass Pinellas's broken EMSE hook.
Agent 3's research suggests /v4/search/parcels and /v4/search/addresses use
different event handlers than /v4/search/records — if those work we can
reverse-map parcels to record IDs."""
import os
import requests
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

headers = {"Authorization": token, "Content-Type": "application/json",
           "x-accela-appid": CLIENT_ID, "x-accela-agency": "PINELLAS"}

print("=" * 80)
print("TESTING ALTERNATIVE V4 ENDPOINTS AGAINST PINELLAS")
print("=" * 80)

def hit(label, method, path, params=None, body=None):
    url = f"https://apis.accela.com{path}"
    if method == "GET":
        r = requests.get(url, params=params, headers=headers, timeout=20)
    else:
        r = requests.post(url, params=params, json=body or {}, headers=headers, timeout=20)
    try:
        data = r.json()
        result = data.get("result")
        count = len(result) if isinstance(result, list) else ("dict" if isinstance(result, dict) else "?")
        err = data.get("code") if r.status_code != 200 else None
        preview = str(result)[:200] if result else ""
    except Exception:
        count = "?"
        err = "parse_err"
        preview = r.text[:150]
    print(f"\n  [{label}] {method} {path}")
    print(f"    HTTP {r.status_code} | count={count} | err={err}")
    if preview and r.status_code == 200:
        print(f"    preview: {preview}")
    elif err:
        print(f"    body: {r.text[:150]}")
    return r

# ============ PHASE 1: endpoints that Agent 3 suggested may bypass the broken EMSE ==========
print("\nPHASE 1: Alternative search endpoints (Agent 3 hypothesis)")
hit("search parcels (body)", "POST", "/v4/search/parcels", {"limit": 3}, {})
hit("search addresses (body)", "POST", "/v4/search/addresses", {"limit": 3}, {"streetStart": 1})
hit("search professionals", "POST", "/v4/search/professionals", {"limit": 3}, {})
hit("search owners", "POST", "/v4/search/owners", {"limit": 3}, {})
hit("search contacts", "POST", "/v4/search/contacts", {"limit": 3}, {})
hit("search inspections", "POST", "/v4/search/inspections", {"limit": 3}, {})
hit("search workflow tasks", "POST", "/v4/search/workflowTasks", {"limit": 3}, {})

# ============ PHASE 2: GET-style records endpoints ==========
print("\n\nPHASE 2: GET-style record endpoints (different event hooks)")
hit("GET /v4/records (empty)", "GET", "/v4/records", {"limit": 1})
hit("GET /v4/records with module", "GET", "/v4/records", {"limit": 1, "module": "Building"})
hit("GET /v4/records/types", "GET", "/v4/records/types")
hit("GET /v4/settings/modules", "GET", "/v4/settings/modules")
hit("GET /v4/agencies/PINELLAS/modules", "GET", "/v4/agencies/PINELLAS/modules")
hit("GET /v4/agencies/PINELLAS/appSettings", "GET", "/v4/agencies/PINELLAS/appSettings")

# ============ PHASE 3: maybe settings endpoints reveal what's allowed ==========
print("\n\nPHASE 3: Settings & discovery endpoints")
hit("GET /v4/search/records/searchable",  "GET", "/v4/search/records/searchable")
hit("GET /v4/search/records/events", "GET", "/v4/search/records/events")
hit("GET /v4/settings/records/types", "GET", "/v4/settings/records/types")

# ============ PHASE 4: me endpoints (user context) ==========
print("\n\nPHASE 4: 'Me' endpoints (user-scoped, may differ from records scope)")
hit("GET /v4/me", "GET", "/v4/me")
hit("GET /v4/me/records", "GET", "/v4/me/records", {"limit": 3})
hit("GET /v4/me/inspections", "GET", "/v4/me/inspections", {"limit": 3})

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
