#!/usr/bin/env python3
"""Re-auth with broader OAuth scopes and test parcel/address endpoints.
The hypothesis: /records* endpoints hit a broken EMSE script, but
/search/parcels, /search/addresses etc. use different event hooks and may work
if we request the right scopes."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
USERNAME = os.getenv("ACCELA_HCFL_USERNAME")
PASSWORD = os.getenv("ACCELA_HCFL_PASSWORD")

# Try a bunch of scope combinations — space separated per OAuth standard
scopes_to_try = [
    "records",  # baseline
    "records search_addresses",
    "records search_parcels",
    "records search_owners",
    "records search_professionals",
    "search_addresses search_parcels search_owners",
    "records get_records search_records search_addresses search_parcels search_owners search_professionals search_contacts search_inspections get_settings_addresses get_settings_professionals get_parcels get_addresses",
]

print("=" * 80)
print("OAUTH SCOPE EXPANSION — find what scopes work for PINELLAS")
print("=" * 80)

def auth_with_scope(scope):
    r = requests.post("https://auth.accela.com/oauth2/token",
        data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
              "username": USERNAME, "password": PASSWORD, "scope": scope,
              "agency_name": "PINELLAS", "environment": "PROD"},
        headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
        timeout=30)
    return r.status_code, r.json() if 'application/json' in r.headers.get('content-type', '') else {"raw": r.text}

working_tokens = {}
for s in scopes_to_try:
    code, body = auth_with_scope(s)
    if code == 200:
        granted_scope = body.get('scope', '?')
        print(f"\n  ✅ '{s}' → token granted (scope returned: '{granted_scope}')")
        working_tokens[s] = body["access_token"]
    else:
        err = body.get('error', body.get('code', '?'))
        desc = body.get('error_description', body.get('message', ''))[:120]
        print(f"\n  ❌ '{s}' → HTTP {code}, err={err}, msg={desc}")

# Now, with the BROADEST successful token, test all endpoints
if working_tokens:
    # Pick widest scope that worked
    scope_lengths = [(s, len(s)) for s in working_tokens.keys()]
    widest_scope = max(scope_lengths, key=lambda x: x[1])[0]
    token = working_tokens[widest_scope]
    print(f"\n\n" + "=" * 80)
    print(f"USING BROADEST WORKING SCOPE: '{widest_scope}'")
    print(f"=" * 80)

    headers = {"Authorization": token, "Content-Type": "application/json",
               "x-accela-appid": CLIENT_ID, "x-accela-agency": "PINELLAS"}

    endpoints = [
        ("POST", "/v4/search/parcels", {}, "parcels"),
        ("POST", "/v4/search/addresses", {"streetStart": 1, "streetEnd": 9999}, "addresses"),
        ("POST", "/v4/search/owners", {}, "owners"),
        ("POST", "/v4/search/professionals", {}, "professionals"),
        ("POST", "/v4/search/contacts", {}, "contacts"),
        ("POST", "/v4/search/inspections", {}, "inspections"),
        ("GET", "/v4/parcels", None, "parcels list"),
        ("GET", "/v4/addresses", None, "addresses list"),
    ]

    for method, path, body, label in endpoints:
        try:
            if method == "POST":
                r = requests.post(f"https://apis.accela.com{path}",
                                  params={"limit": 5}, json=body, headers=headers, timeout=30)
            else:
                r = requests.get(f"https://apis.accela.com{path}",
                                 params={"limit": 5}, headers=headers, timeout=30)
            try:
                data = r.json()
                result = data.get("result")
                count = len(result) if isinstance(result, list) else ("?" if result else 0)
                err = data.get("code") if r.status_code != 200 else None
            except Exception:
                count = "?"
                err = "parse_err"
            status_icon = "✅" if r.status_code == 200 and isinstance(count, int) and count > 0 else ("⚪" if r.status_code == 200 else "❌")
            print(f"\n  {status_icon} {method} {path}")
            print(f"    HTTP {r.status_code} | count={count} | err={err}")
            if r.status_code == 200 and count and isinstance(count, int) and count > 0:
                # Show sample record
                sample = data["result"][0]
                sample_keys = list(sample.keys())[:15] if isinstance(sample, dict) else []
                print(f"    sample keys: {sample_keys}")
                if 'parcelNumber' in sample:
                    print(f"    parcelNumber: {sample.get('parcelNumber')}")
                if 'addressLine1' in sample:
                    print(f"    address: {sample.get('addressLine1', '')} {sample.get('city','')} {sample.get('postalCode','')}")
            elif r.status_code != 200:
                print(f"    body: {r.text[:150]}")
        except Exception as e:
            print(f"  EXCEPTION: {e}")

print("\n" + "=" * 80)
print("DONE")
