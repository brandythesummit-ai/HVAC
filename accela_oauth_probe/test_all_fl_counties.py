#!/usr/bin/env python3
"""Test Accela V4 API against every FL county on aca-prod.accela.com using the
same citizen account. For each: (1) can we auth? (2) does POST /v4/search/records
work or 500? (3) if it works, what's the sample data look like?"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("ACCELA_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACCELA_CLIENT_SECRET")
USERNAME = os.getenv("ACCELA_HCFL_USERNAME")
PASSWORD = os.getenv("ACCELA_HCFL_PASSWORD")

# From spreadsheet — FL counties using aca-prod.accela.com
AGENCIES = [
    ("HCFL",     "Hillsborough County"),   # control — known working
    ("PINELLAS", "Pinellas County"),       # known 500
    ("BOCC",     "Charlotte County"),
    ("LEECO",    "Lee County"),
    ("LEONCO",   "Leon County"),
    ("MARTINCO", "Martin County"),
    ("PASCO",    "Pasco County"),
    ("POLKCO",   "Polk County"),
    ("SARASOTA", "Sarasota County"),
]

def auth(agency_code):
    """Password grant for a given agency."""
    r = requests.post("https://auth.accela.com/oauth2/token",
        data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
              "username": USERNAME, "password": PASSWORD, "scope": "records",
              "agency_name": agency_code, "environment": "PROD"},
        headers={"Content-Type": "application/x-www-form-urlencoded", "x-accela-appid": CLIENT_ID},
        timeout=30)
    return r

def query_records(agency_code, token):
    """Simple POST /v4/search/records test — 2024 permits, module=Building."""
    return requests.post("https://apis.accela.com/v4/search/records",
        params={"limit": 3},
        json={"module": "Building", "openedDateFrom": "2024-01-01", "openedDateTo": "2024-12-31"},
        headers={"Authorization": token, "Content-Type": "application/json",
                 "x-accela-appid": CLIENT_ID, "x-accela-agency": agency_code},
        timeout=30)

def query_agency_metadata(agency_code):
    """GET /v4/agencies/{code} — no user auth needed."""
    return requests.get(f"https://apis.accela.com/v4/agencies/{agency_code}",
        headers={"x-accela-appid": CLIENT_ID, "x-accela-appsecret": CLIENT_SECRET},
        timeout=15)

print("=" * 100)
print(f"{'Agency':<10} {'County':<25} {'Metadata':<10} {'Auth':<10} {'Records API':<20} {'# records':<10} {'Notes'}")
print("=" * 100)

summary = []
for code, name in AGENCIES:
    # Metadata check (no user auth)
    meta_r = query_agency_metadata(code)
    meta_ok = "✅ 200" if meta_r.status_code == 200 else f"❌ {meta_r.status_code}"

    # Auth check
    auth_r = auth(code)
    if auth_r.status_code == 200:
        token = auth_r.json().get("access_token")
        auth_ok = "✅"
    else:
        token = None
        try:
            err = auth_r.json().get("error_description", auth_r.json().get("message", "unknown"))[:40]
        except Exception:
            err = auth_r.text[:40]
        auth_ok = f"❌ {auth_r.status_code}"

    # Records API check
    records_status = "—"
    records_count = "—"
    notes = ""
    if token:
        rec_r = query_records(code, token)
        if rec_r.status_code == 200:
            try:
                data = rec_r.json()
                results = data.get("result") or []
                records_count = str(len(results))
                records_status = "✅ 200"
            except Exception:
                records_status = "✅ 200 (parse err)"
        elif rec_r.status_code == 500:
            records_status = "❌ 500 EMSE"
            try:
                notes = "trace=" + rec_r.json().get("traceId", "?")[:25]
            except Exception:
                notes = "500"
        else:
            records_status = f"❌ {rec_r.status_code}"
            try:
                notes = rec_r.json().get("code", "") + " " + rec_r.json().get("message", "")[:30]
            except Exception:
                notes = rec_r.text[:30]
    else:
        records_status = "skip"
        notes = err if 'err' in locals() else ""

    print(f"{code:<10} {name:<25} {meta_ok:<10} {auth_ok:<10} {records_status:<20} {records_count:<10} {notes}")
    summary.append((code, name, meta_r.status_code, auth_r.status_code, records_status))

print("=" * 100)

# Summary tally
working_count = sum(1 for s in summary if "✅" in s[4])
broken_count = sum(1 for s in summary if "❌ 500" in s[4])
total = len(summary)

print(f"\nSUMMARY:")
print(f"  Agencies tested: {total}")
print(f"  Records API working: {working_count}")
print(f"  Records API blocked (500): {broken_count}")
print(f"  Other failures: {total - working_count - broken_count}")

# For any that worked, show a sample record
print(f"\nFor working agencies, here's a sample 2024 Building permit:")
for code, name, _, _, status in summary:
    if "✅" in status:
        auth_r = auth(code)
        if auth_r.status_code == 200:
            token = auth_r.json()["access_token"]
            r = query_records(code, token)
            if r.status_code == 200:
                recs = r.json().get("result", [])
                if recs:
                    p = recs[0]
                    t = p.get("type", {})
                    print(f"\n  [{code}] {name}")
                    print(f"    customId: {p.get('customId')}")
                    print(f"    type.value: {t.get('value') if isinstance(t, dict) else t}")
                    print(f"    type.text: {t.get('text') if isinstance(t, dict) else ''}")
                    print(f"    openedDate: {p.get('openedDate','')[:10]}")
