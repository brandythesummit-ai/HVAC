#!/usr/bin/env python3
"""
Per docs: token has agency/environment embedded. Maybe sending
x-accela-agency explicitly causes a mismatch with what's in the token.
Test: mint a per-agency token and call search WITHOUT x-accela-agency header.
Also: decode the token to see what's embedded in it.
"""
import os, base64, json, requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
USERNAME = os.getenv("ACCELA_HCFL_USERNAME")
PASSWORD = os.getenv("ACCELA_HCFL_PASSWORD")

def get_token(agency):
    """Password grant for a specific agency."""
    r = requests.post("https://auth.accela.com/oauth2/token",
        data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
              "username": USERNAME, "password": PASSWORD, "scope": "records",
              "agency_name": agency, "environment": "PROD"},
        headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
        timeout=30)
    if r.status_code != 200:
        return None, None
    return r.json().get("access_token"), r.json()

def decode_jwt_payload(token):
    """Accela tokens may be JWTs — decode the payload if so. Otherwise return None."""
    try:
        parts = token.split(".")
        if len(parts) == 3:
            payload = parts[1]
            payload += "=" * (4 - len(payload) % 4)  # pad for base64
            decoded = base64.urlsafe_b64decode(payload).decode()
            return json.loads(decoded)
    except Exception as e:
        return {"_error": str(e)}
    return None

def search(token, agency_header=None, env_header=None):
    """Search records with variations on headers."""
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "x-accela-appid": CLIENT_ID,
    }
    if agency_header:
        headers["x-accela-agency"] = agency_header
    if env_header:
        headers["x-accela-environment"] = env_header
    r = requests.post(
        "https://apis.accela.com/v4/search/records",
        params={"limit": 3},
        json={"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2024-12-31"},
        headers=headers, timeout=30)
    return r

def _parse(r):
    try:
        b = r.json()
        if r.status_code == 200:
            n = len(b.get("result", []) or [])
            return f"SUCCESS n={n}"
        return f"{b.get('code','?')} | {b.get('message','')[:60]}"
    except Exception:
        return r.text[:80]

AGENCIES = ["HCFL", "PINELLAS", "LEECO", "PASCO"]

print("=" * 100)
print("TEST: per-agency token decoding + search variations")
print("=" * 100)

for ag in AGENCIES:
    print(f"\n━━━ {ag} ━━━")
    tok, full = get_token(ag)
    if not tok:
        print(f"  Token acquisition failed")
        continue

    # Decode if JWT
    payload = decode_jwt_payload(tok)
    if payload:
        print(f"  Token decoded fields: {json.dumps(payload, default=str)[:200]}")
    else:
        print(f"  Token is NOT a JWT (opaque). Full response keys: {list(full.keys())}")
        # Show what agency/env info came back in the token response
        print(f"    agency_name in response: {full.get('agency_name')}")
        print(f"    environment in response: {full.get('environment')}")
        print(f"    scope: {full.get('scope')}")

    # Now try variations
    # V1: token + NO agency header + NO env header (rely on token)
    r1 = search(tok)
    print(f"  V1 (token only, no headers): HTTP {r1.status_code} | {_parse(r1)}")

    # V2: token + x-accela-agency only
    r2 = search(tok, agency_header=ag)
    print(f"  V2 (token + agency): HTTP {r2.status_code} | {_parse(r2)}")

    # V3: token + env only
    r3 = search(tok, env_header="PROD")
    print(f"  V3 (token + env): HTTP {r3.status_code} | {_parse(r3)}")

    # V4: token + agency + env
    r4 = search(tok, agency_header=ag, env_header="PROD")
    print(f"  V4 (token + agency + env): HTTP {r4.status_code} | {_parse(r4)}")
