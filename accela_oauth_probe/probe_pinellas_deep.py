#!/usr/bin/env python3
"""Deep probe of Pinellas API surface — find what modules/endpoints actually work."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
USERNAME = os.getenv("ACCELA_HCFL_USERNAME")
PASSWORD = os.getenv("ACCELA_HCFL_PASSWORD")
API_BASE = "https://apis.accela.com"

def auth(agency):
    r = requests.post("https://auth.accela.com/oauth2/token",
        data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
              "username": USERNAME, "password": PASSWORD, "scope": "records",
              "agency_name": agency, "environment": "PROD"},
        headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
        timeout=30)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:200]}"
    return r.json()["access_token"], None

def try_endpoint(agency, token, method, path, body=None, params=None):
    headers = {"Authorization": token, "Content-Type": "application/json",
               "x-accela-appid": CLIENT_ID, "x-accela-agency": agency}
    if method == "GET":
        r = requests.get(f"{API_BASE}{path}", params=params, headers=headers, timeout=20)
    else:
        r = requests.post(f"{API_BASE}{path}", params=params, json=body or {}, headers=headers, timeout=20)
    return r

print("=" * 80)
print("DEEP PROBE: PINELLAS API SURFACE")
print("=" * 80)

tok_pin, err = auth("PINELLAS")
if err:
    print(f"Auth failed: {err}")
    exit(1)
print(f"✅ PINELLAS auth OK\n")

# 1. List agency-available modules (if endpoint exists)
print("[1] /v4/agencies/PINELLAS (what do we see?)")
r = try_endpoint("PINELLAS", tok_pin, "GET", "/v4/agencies/PINELLAS")
if r.status_code == 200:
    data = r.json().get("result", {})
    print(f"   enabled={data.get('enabled')} defaultAppActive={data.get('defaultAppActive')}")
    print(f"   display={data.get('display')} hostedACA={data.get('hostedACA')}")
print()

# 2. Try listing record types via the v4 endpoint
print("[2] /v4/agencies/PINELLAS/recordTypes?module=X (various modules)")
for mod in ["Building", "DRS", "Enforcement", "Licenses", "Planning", "ServiceRequest", "Public Works"]:
    r = try_endpoint("PINELLAS", tok_pin, "GET", "/v4/agencies/PINELLAS/recordTypes",
                     params={"module": mod, "limit": 5})
    try:
        body = r.json()
        types = body.get("result") or []
        print(f"   module={mod:<18}: HTTP {r.status_code}, types={len(types) if isinstance(types, list) else '?'}")
        if types and len(types) > 0:
            for t in types[:3]:
                print(f"       - {t.get('value', '?')}")
    except Exception:
        print(f"   module={mod:<18}: HTTP {r.status_code}, body={r.text[:80]}")
print()

# 3. Try a record-type search without a module filter at all
print("[3] /v4/search/records with NO module filter")
r = try_endpoint("PINELLAS", tok_pin, "POST", "/v4/search/records",
                 params={"limit": 3}, body={})
print(f"   HTTP {r.status_code}, body={r.text[:200]}")
print()

# 4. Try GET /v4/records (different endpoint)
print("[4] GET /v4/records")
r = try_endpoint("PINELLAS", tok_pin, "GET", "/v4/records",
                 params={"limit": 3, "openedDateFrom": "2025-01-01", "openedDateTo": "2025-12-31"})
print(f"   HTTP {r.status_code}, body={r.text[:300]}")
print()

# 5. Try looking up a known Pinellas permit by customId pattern (if we had any)
print("[5] GET /v4/records/byId/{id} — attempt direct lookup")
for cid in ["BLD2024-00001", "BCP24-00001", "24-00001"]:
    r = try_endpoint("PINELLAS", tok_pin, "GET", "/v4/records",
                     params={"customId": cid, "limit": 1})
    print(f"   customId='{cid}': HTTP {r.status_code}, body preview={r.text[:120]}")
print()

# 6. Try another agency name entirely — e.g., CLEARWATER (city within Pinellas)
print("=" * 80)
print("BONUS: CLEARWATER (a city inside Pinellas — does it host its own Accela permits?)")
print("=" * 80)
tok_cw, err_cw = auth("CLEARWATER")
if err_cw:
    print(f"CLEARWATER auth failed: {err_cw}")
else:
    print(f"✅ CLEARWATER auth OK")
    r = try_endpoint("CLEARWATER", tok_cw, "POST", "/v4/search/records",
                     params={"limit": 5},
                     body={"module": "Building", "openedDateFrom": "2025-01-01", "openedDateTo": "2025-12-31"})
    try:
        data = r.json()
        count = len(data.get("result", []) or [])
        print(f"   Building permits 2025: HTTP {r.status_code}, count={count}")
        if count > 0:
            p = data["result"][0]
            t = p.get("type", {})
            print(f"   Sample: customId={p.get('customId')} type={t.get('value') if isinstance(t, dict) else t}")
    except Exception as e:
        print(f"   Error: {e} — body={r.text[:200]}")

# 7. Try ST_PETE or ST-PETE or STPETE as other Pinellas cities
print()
print("=" * 80)
print("BONUS: Other Pinellas cities")
print("=" * 80)
for city_agency in ["STPETE", "ST_PETE", "SAINT_PETERSBURG", "ST_PETERSBURG", "LARGO", "DUNEDIN", "SEMINOLE"]:
    tok, err_c = auth(city_agency)
    if err_c:
        # Just show short diagnostic
        code = err_c[:20]
        print(f"   {city_agency}: auth fail ({code}...)")
    else:
        r = try_endpoint(city_agency, tok, "POST", "/v4/search/records",
                        params={"limit": 3},
                        body={"module": "Building", "openedDateFrom": "2025-01-01", "openedDateTo": "2025-12-31"})
        try:
            count = len(r.json().get("result", []) or [])
        except Exception:
            count = "?"
        print(f"   {city_agency}: auth OK, Building 2025 search → HTTP {r.status_code}, count={count}")
