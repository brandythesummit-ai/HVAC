"""Populate the hcfl_streets table from US Census TIGER/Line road data.

The HCFL legacy scraper (M5) iterates over unique street names to pull
historical permits. We need an authoritative, reproducible list.

Source: US Census TIGER/Line roads for Hillsborough County, FL (FIPS 12057).
  - Free, stable, government data.
  - Small (~3-4 MB ZIP) — fast to re-download on schedule.
  - Filtered by MTFCC to exclude interstates/ramps/trails/private drives.

Usage:
    cd backend && source venv/bin/activate
    python -m scripts.build_hcfl_streets
        [--year 2025]        # TIGER year; default: auto-detect latest
        [--dry-run]          # print would-insert rows, don't touch DB
        [--cache-dir DIR]    # default: /tmp/hcfl_streets_cache

Idempotent: running it twice with the same data produces no DB changes
(existing street_name rows are skipped via ON CONFLICT DO NOTHING).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.hcfl_streets import TIGER_STREET_MTFCC, normalize_street  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("build_hcfl_streets")

HILLSBOROUGH_FIPS = "12057"
TIGER_URL_TEMPLATE = (
    "https://www2.census.gov/geo/tiger/TIGER{year}/ROADS/"
    "tl_{year}_{fips}_roads.zip"
)


def detect_latest_tiger_year(start: int | None = None, floor: int = 2020) -> int:
    # Walk backward from next year until we hit a TIGER dataset that exists.
    # Using next year as the starting point means the probe stays fresh
    # forever — when Census publishes TIGER 2028, we pick it up automatically.
    if start is None:
        start = datetime.now().year + 1
    with httpx.Client(timeout=10.0) as client:
        for year in range(start, floor - 1, -1):
            url = TIGER_URL_TEMPLATE.format(year=year, fips=HILLSBOROUGH_FIPS)
            try:
                resp = client.head(url)
                if resp.status_code == 200:
                    log.info("Detected latest TIGER year: %d", year)
                    return year
            except httpx.HTTPError as exc:
                log.warning("HEAD %s failed: %s", url, exc)
    raise RuntimeError(f"No TIGER year between {floor} and {start} found for FIPS {HILLSBOROUGH_FIPS}")


def download_tiger_zip(year: int, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"tl_{year}_{HILLSBOROUGH_FIPS}_roads.zip"
    if target.exists() and target.stat().st_size > 0:
        log.info("Using cached ZIP: %s (%d bytes)", target, target.stat().st_size)
        return target

    url = TIGER_URL_TEMPLATE.format(year=year, fips=HILLSBOROUGH_FIPS)
    log.info("Downloading %s ...", url)
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with target.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)
    log.info("Downloaded %d bytes to %s", target.stat().st_size, target)
    return target


def extract_streets_from_shapefile(zip_path: Path) -> set[str]:
    # Import inside the function so the script can surface a clear error
    # if pyshp is missing (requirements.txt is the source of truth).
    import shapefile  # pyshp

    log.info("Extracting street names from %s", zip_path)
    streets: set[str] = set()
    raw_sample: list[str] = []  # for logging a few raw pre-normalization

    # pyshp can read directly from a ZIP if we pass opened file-like
    # handles for .shp, .shx, .dbf. Simpler: unzip to a temp dir.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_path)
        # Find the .shp file
        shp_files = list(tmp_path.glob("*.shp"))
        if not shp_files:
            raise RuntimeError(f"No .shp file found in {zip_path}")
        shp = shp_files[0]
        log.info("Reading %s", shp)

        reader = shapefile.Reader(str(shp.with_suffix("")))  # pyshp takes path without extension
        fields = [f[0] for f in reader.fields[1:]]  # skip DeletionFlag
        log.info("Shapefile fields: %s", fields)

        fullname_idx = fields.index("FULLNAME") if "FULLNAME" in fields else None
        mtfcc_idx = fields.index("MTFCC") if "MTFCC" in fields else None
        if fullname_idx is None:
            raise RuntimeError("FULLNAME field not found in shapefile")

        total_records = 0
        filtered = 0
        for record in reader.iterRecords():
            total_records += 1
            fullname = record[fullname_idx]
            if not fullname:
                continue
            if mtfcc_idx is not None:
                mtfcc = record[mtfcc_idx]
                if mtfcc not in TIGER_STREET_MTFCC:
                    filtered += 1
                    continue
            normalized = normalize_street(fullname)
            if normalized:
                if len(raw_sample) < 5:
                    raw_sample.append(f"{fullname!r} -> {normalized!r}")
                streets.add(normalized)
        log.info(
            "Processed %d records (filtered %d by MTFCC), %d unique streets",
            total_records,
            filtered,
            len(streets),
        )
        log.info("Sample normalizations: %s", raw_sample)
    return streets


def upsert_streets(streets: set[str], dry_run: bool = False) -> dict:
    # Keep import local so tests that import utility functions from this
    # script don't require supabase env to be configured.
    from supabase import create_client

    sup_url = os.environ.get("SUPABASE_URL")
    sup_key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not sup_url or not sup_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")

    if dry_run:
        log.info("[DRY RUN] Would upsert %d streets. First 10: %s",
                 len(streets), sorted(streets)[:10])
        return {"inserted": 0, "skipped": len(streets), "dry_run": True}

    client = create_client(sup_url, sup_key)
    # Use upsert with ignore_duplicates via on_conflict on the UNIQUE street_name
    rows = [{"street_name": s} for s in sorted(streets)]
    # Supabase's python client doesn't support ON CONFLICT DO NOTHING directly;
    # we use upsert with ignore_duplicates=True which rpc'es to INSERT ... ON CONFLICT DO NOTHING.
    batch_size = 500
    total_inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        resp = client.table("hcfl_streets").upsert(
            batch, on_conflict="street_name", ignore_duplicates=True
        ).execute()
        total_inserted += len(resp.data or [])
        log.info(
            "Batch %d/%d: %d rows returned",
            (i // batch_size) + 1,
            (len(rows) + batch_size - 1) // batch_size,
            len(resp.data or []),
        )
    log.info("Upsert complete. Rows returned: %d (new inserts; existing rows are skipped)",
             total_inserted)
    return {"inserted": total_inserted, "total_candidates": len(streets)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None,
                        help="TIGER year. Default: auto-detect latest available.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip DB upsert; print what would be inserted.")
    parser.add_argument("--cache-dir", default="/tmp/hcfl_streets_cache",
                        help="Where to cache the downloaded TIGER ZIP.")
    args = parser.parse_args()

    # Load .env if present (script-like tooling convenience).
    try:
        from dotenv import load_dotenv
        dotenv_path = Path(__file__).parent.parent / ".env"
        if dotenv_path.exists():
            load_dotenv(dotenv_path)
    except ImportError:
        pass

    year = args.year or detect_latest_tiger_year()
    zip_path = download_tiger_zip(year, Path(args.cache_dir))
    streets = extract_streets_from_shapefile(zip_path)
    result = upsert_streets(streets, dry_run=args.dry_run)
    log.info("Done. Result: %s", result)


if __name__ == "__main__":
    main()
