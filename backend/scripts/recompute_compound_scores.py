"""One-shot script: recompute compound scores on all residential
properties. Drives the recompute_compound_scores_chunk() RPC (added
in migration 063) in a loop until no rows remain to update.

When to run:
  - After migration 063 first applies (initial bulk recompute)
  - After any change to the score_property() function logic that
    changes how scores are computed
  - After bulk imports that bypassed the BEFORE INSERT trigger

Strategy:
  1. Call /rpc/recompute_compound_scores_chunk → returns rows updated
  2. Repeat until it returns 0
  3. Refresh map_snapshot_mv via /rpc/refresh_map_snapshot

Why a loop instead of a single bulk UPDATE:
  - 350K rows × leads-sync trigger from migration 058 = ~700K row writes
  - Exceeds Supabase's 8s PostgREST statement_timeout in one call
  - Chunked to 5K rows per call (~7-12s each); the function disables
    its own statement_timeout via `SET statement_timeout TO 0`

Usage:
  cd backend && python scripts/recompute_compound_scores.py

Requires SUPABASE_URL + SUPABASE_KEY (service-role) in backend/.env.
"""
import os
import sys
import time
from pathlib import Path

# Load .env from backend/
env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("SUPABASE_") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k] = v.strip()

import httpx

URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_KEY"]
HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

CHUNK_SIZE = 5000  # Each chunk completes in ~7-12s; safe under any timeout


def post_rpc(name, body):
    r = httpx.post(f"{URL}/rest/v1/rpc/{name}", headers=HEADERS, json=body, timeout=600)
    r.raise_for_status()
    return r.json()


def main():
    print(f"Recomputing compound scores in chunks of {CHUNK_SIZE}...")
    total = 0
    iteration = 0
    start = time.time()

    while True:
        iteration += 1
        t0 = time.time()
        n = post_rpc("recompute_compound_scores_chunk", {"p_chunk_size": CHUNK_SIZE})
        if not isinstance(n, int):
            n = int(n)
        dt = time.time() - t0
        total += n
        print(f"  chunk {iteration:>3}: {n:>5} rows in {dt:.1f}s  (total: {total})")
        if n == 0:
            break

    print(f"\nDone. Updated {total} rows in {time.time() - start:.1f}s.")

    print("Refreshing map_snapshot_mv...")
    t0 = time.time()
    refresh = post_rpc("refresh_map_snapshot", {})
    print(f"  {refresh}  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
