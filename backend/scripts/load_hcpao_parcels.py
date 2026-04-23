"""Load HCPAO parcel data into `properties` — residential only.

This is the seed loader for the parcels-first architecture. Downloads the
Hillsborough County Property Appraiser's weekly parcel DBF plus the
companion lat/lng centroid file, filters to residential DOR codes, and
bulk-upserts into the properties table keyed on (county_id, folio).

HCPAO's directory page (https://downloads.hcpafl.org) is served as an
ASP.NET page where the file rows are __doPostBack handlers — direct GETs
of the zip filename 404. The loader replicates the postback:
  1. GET / to parse the file list and capture the hidden form tokens
     (__VIEWSTATE, __VIEWSTATEGENERATOR, __EVENTVALIDATION).
  2. POST / with __EVENTTARGET = the row's ctl number to receive the zip.

Residential filter (FL Department of Revenue property use codes used by
HCPA — confirmed against parcel_dor_names.dbf on 2026-04-23):
    0100 SFR      (~355K)
    0102 SFR built around MH
    0106 Townhouse/Villa
    0111 New Res permit
    0200 Mobile Home
    0400 Condominium
    0403 Condo Apt
    0408 MH Condo
    0500 Co-op
    0508 MH Co-op

Total residential ≈ 450K of the 531K parcel rows.

Usage:
    cd backend && source venv/bin/activate
    python -m scripts.load_hcpao_parcels
        [--cache-dir PATH]      # where to save downloads (default /tmp/hcpao_cache)
        [--county-id UUID]      # default HCFL
        [--limit N]             # load only first N residential rows (smoke test)
        [--skip-download]       # reuse cached zips if present
        [--batch-size N]        # upsert batch size (default 500)
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import zipfile
from datetime import datetime, date
from pathlib import Path

import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("load_hcpao")

HCFL_COUNTY_ID = "07e876b9-938e-4f53-b0dc-7bb9ce7e9cdd"
HCPAO_BASE = "https://downloads.hcpafl.org"

# Residential FL DOR use codes — loaded into properties with is_residential=true.
RESIDENTIAL_DOR_CODES = {
    "0100",  # Single Family Residential (~355K)
    "0102",  # SFR built around Mobile Home
    "0106",  # Townhouse / Villa
    "0111",  # New Residential permit
    "0200",  # Mobile Home (~13K)
    "0400",  # Condominium (~40K)
    "0403",  # Condo Apt
    "0408",  # Mobile Home Condo
    "0500",  # Co-op
    "0508",  # MH Co-op
}

# HCFL geographic bounding box (coarse). Parcels whose HCPAO-supplied
# centroid falls outside this box are treated as data errors (they shouldn't
# exist for a Hillsborough County parcel, but we defend in depth).
HCFL_BBOX = {
    "lat_min": 27.5, "lat_max": 28.2,
    "lng_min": -82.9, "lng_max": -82.0,
}


def _fetch_directory_page(client: httpx.Client) -> tuple[str, dict]:
    """Return (html_body, form_tokens) from the directory page."""
    resp = client.get("/")
    resp.raise_for_status()
    html = resp.text
    tokens = {}
    for key in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
        match = re.search(rf'{key}" value="([^"]*)"', html)
        if not match:
            raise RuntimeError(f"Could not find {key} on HCPAO directory page")
        tokens[key] = match.group(1)
    return html, tokens


def _discover_postback_targets(html: str) -> dict[str, str]:
    """Map filename → __EVENTTARGET ctl number.

    HCPAO's table rows look like:
      <td>...<a href="javascript:__doPostBack('grdFiles$ctl00$ctl20$ctl00','')">
        <i class='bi bi-file-earmark-zip'></i> parcel_04_17_2026.zip</a>...</td>
    """
    targets: dict[str, str] = {}
    pattern = re.compile(
        r"__doPostBack\(&#39;(grdFiles\$ctl00\$ctl\d+\$ctl00)&#39;,[^)]*\)"
        r"[^<]*<i[^>]*></i>\s*([A-Za-z0-9_.]+\.zip)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        targets[match.group(2)] = match.group(1)
    return targets


def _find_latest(targets: dict[str, str], prefix: str) -> tuple[str, str]:
    """Find the newest filename for a prefix like 'parcel_' or 'LatLon_Table_'.

    Filenames encode the date as MM_DD_YYYY. Return (filename, event_target).
    """
    candidates = [f for f in targets if f.lower().startswith(prefix.lower())]
    if not candidates:
        raise RuntimeError(f"No files matching prefix {prefix!r} on HCPAO directory")

    def _key(fname: str) -> date:
        m = re.search(r"(\d{2})_(\d{2})_(\d{4})", fname)
        if not m:
            return date.min
        mo, d, y = (int(x) for x in m.groups())
        return date(y, mo, d)

    newest = max(candidates, key=_key)
    return newest, targets[newest]


def _download_via_postback(
    client: httpx.Client,
    event_target: str,
    tokens: dict,
    out_path: Path,
) -> None:
    """POST the directory page with __EVENTTARGET and save the body to disk."""
    logger.info("POST postback for %s → %s", event_target, out_path.name)
    with client.stream(
        "POST", "/",
        data={
            "__EVENTTARGET": event_target,
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": tokens["__VIEWSTATE"],
            "__VIEWSTATEGENERATOR": tokens["__VIEWSTATEGENERATOR"],
            "__EVENTVALIDATION": tokens["__EVENTVALIDATION"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=600.0,
    ) as resp:
        resp.raise_for_status()
        total = 0
        with out_path.open("wb") as fh:
            for chunk in resp.iter_bytes(chunk_size=65536):
                fh.write(chunk)
                total += len(chunk)
        logger.info("  downloaded %d bytes", total)


def download_parcel_archives(cache_dir: Path) -> tuple[Path, Path]:
    """Fetch the latest parcel and latlon ZIPs into cache_dir.

    Returns paths to (parcel.zip, latlon.zip). Skips download if files
    already exist (bytes > 0).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=HCPAO_BASE, follow_redirects=True) as client:
        html, tokens = _fetch_directory_page(client)
        targets = _discover_postback_targets(html)
        if not targets:
            raise RuntimeError("Failed to parse any file targets from HCPAO page")

        parcel_fname, parcel_target = _find_latest(targets, "parcel_")
        latlon_fname, latlon_target = _find_latest(targets, "LatLon_Table_")
        logger.info("Latest parcel file: %s", parcel_fname)
        logger.info("Latest latlon file: %s", latlon_fname)

        parcel_path = cache_dir / parcel_fname
        latlon_path = cache_dir / latlon_fname

        if not parcel_path.exists() or parcel_path.stat().st_size == 0:
            _download_via_postback(client, parcel_target, tokens, parcel_path)
        else:
            logger.info("parcel cached: %s", parcel_path)

        if not latlon_path.exists() or latlon_path.stat().st_size == 0:
            _download_via_postback(client, latlon_target, tokens, latlon_path)
        else:
            logger.info("latlon cached: %s", latlon_path)

    return parcel_path, latlon_path


def extract_dbfs(
    parcel_zip: Path, latlon_zip: Path, work_dir: Path
) -> tuple[Path, Path, Path]:
    """Extract parcel.dbf, latlon.dbf, and parcel_dor_names.dbf."""
    work_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(parcel_zip) as zf:
        # Expect 'parcel.dbf' and 'parcel_dor_names.dbf' at least
        for member in zf.namelist():
            if member.lower().endswith(".dbf"):
                zf.extract(member, work_dir)
    with zipfile.ZipFile(latlon_zip) as zf:
        for member in zf.namelist():
            if member.lower().endswith(".dbf"):
                zf.extract(member, work_dir)

    def _find(stem: str) -> Path:
        for path in work_dir.rglob("*.dbf"):
            if path.stem.lower() == stem.lower():
                return path
        raise FileNotFoundError(f"{stem}.dbf not in extracted archives")

    return _find("parcel"), _find("latlon"), _find("parcel_dor_names")


def load_latlon_lookup(latlon_dbf: Path) -> dict[str, tuple[float, float]]:
    """Return {FOLIO: (lat, lng)} — excludes points outside HCFL bbox."""
    from dbfread import DBF
    logger.info("Loading lat/lng lookup from %s", latlon_dbf.name)
    out: dict[str, tuple[float, float]] = {}
    bad = 0
    for row in DBF(str(latlon_dbf), encoding="utf-8", char_decode_errors="ignore"):
        folio = (row.get("FOLIO") or "").strip()
        lat = row.get("lat") or row.get("LAT")
        lng = row.get("lon") or row.get("LON") or row.get("lng")
        if not folio or lat is None or lng is None:
            continue
        lat, lng = float(lat), float(lng)
        if not (HCFL_BBOX["lat_min"] <= lat <= HCFL_BBOX["lat_max"]
                and HCFL_BBOX["lng_min"] <= lng <= HCFL_BBOX["lng_max"]):
            bad += 1
            continue
        out[folio] = (lat, lng)
    logger.info("  loaded %d centroids (%d filtered outside HCFL bbox)", len(out), bad)
    return out


def _as_int(v):
    if v is None or v == "":
        return None
    try:
        iv = int(v)
        return iv if iv > 0 else None
    except (ValueError, TypeError):
        return None


def _as_date(v):
    if not v:
        return None
    if isinstance(v, date):
        return v.isoformat() if v.year > 1900 else None
    try:
        s = str(v).strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return None
    except Exception:
        return None


def build_property_row(
    parcel_row: dict,
    latlon: dict[str, tuple[float, float]],
    county_id: str,
) -> dict | None:
    """Construct a properties-table payload from a parcel.dbf row.

    Returns None if row fails residential filter or has no usable address.
    Performs no database calls.
    """
    folio = (parcel_row.get("FOLIO") or "").strip()
    if not folio:
        return None

    dor = (parcel_row.get("DOR_C") or "").strip()
    if dor not in RESIDENTIAL_DOR_CODES:
        return None

    site_addr = (parcel_row.get("SITE_ADDR") or "").strip().upper()
    if not site_addr:
        # Parcels with no situs address are unusable for door-knocking.
        return None

    normalized = site_addr  # already uppercase; leave structural normalization
                            # to the aggregator on the permit side
    coords = latlon.get(folio)
    lat, lng = (coords if coords else (None, None))

    owner = (parcel_row.get("OWNER") or "").strip() or None
    base = _as_int(parcel_row.get("BASE"))
    year_built = _as_int(parcel_row.get("ACT"))
    heated_sqft = _as_int(parcel_row.get("HEAT_AR"))
    just_val = parcel_row.get("JUST")
    land_val = parcel_row.get("LAND")
    bldg_val = parcel_row.get("BLDG")

    return {
        "county_id": county_id,
        "folio": folio,
        "parcel_number": folio,
        "dor_code": dor,
        "normalized_address": normalized,
        "street_number": None,  # will be populated by address parser later if needed
        "street_name": None,
        "street_suffix": None,
        "city": (parcel_row.get("SITE_CITY") or "").strip() or None,
        "state": "FL",
        "zip_code": (parcel_row.get("SITE_ZIP") or "").strip() or None,
        "owner_name": owner,
        "year_built": year_built,
        "heated_sqft": heated_sqft,
        "bedrooms_count": _as_int(parcel_row.get("tBEDS")),
        "bathrooms_count": parcel_row.get("tBATHS"),
        "stories_count": _as_int(parcel_row.get("tSTORIES")),
        "units_count": _as_int(parcel_row.get("tUNITS")),
        "homestead_year": base,
        "owner_occupied": (base is not None and base > 0),
        "last_sale_date": _as_date(parcel_row.get("S_DATE")),
        "last_sale_amount": parcel_row.get("S_AMT"),
        "land_value": land_val,
        "improved_value": bldg_val,
        "total_property_value": just_val,
        "latitude": lat,
        "longitude": lng,
        "geocoded_at": datetime.utcnow().isoformat() if lat else None,
        "geocode_source": "hcpao_parcel" if lat else None,
        "is_residential": True,
        "source": "hcpao_parcel",
        "total_hvac_permits": 0,  # no permit context yet; Phase 3 populates
    }


def upsert_batch(db, batch: list[dict]) -> None:
    """Upsert a batch keyed on (county_id, folio)."""
    db.table("properties").upsert(
        batch,
        on_conflict="county_id,folio",
        ignore_duplicates=False,
    ).execute()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default="/tmp/hcpao_cache")
    parser.add_argument("--county-id", default=HCFL_COUNTY_ID)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass

    from dbfread import DBF
    from supabase import create_client

    cache_dir = Path(args.cache_dir)

    if args.skip_download:
        parcel_zips = sorted(cache_dir.glob("parcel_*.zip"))
        latlon_zips = sorted(cache_dir.glob("LatLon_Table_*.zip"))
        if not parcel_zips or not latlon_zips:
            raise SystemExit("--skip-download requested but no cached zips found")
        parcel_zip = parcel_zips[-1]
        latlon_zip = latlon_zips[-1]
        logger.info("Using cached parcel=%s, latlon=%s", parcel_zip.name, latlon_zip.name)
    else:
        parcel_zip, latlon_zip = download_parcel_archives(cache_dir)

    work_dir = cache_dir / "extracted"
    parcel_dbf, latlon_dbf, _dor_dbf = extract_dbfs(parcel_zip, latlon_zip, work_dir)
    logger.info("Parcel DBF: %s", parcel_dbf)
    logger.info("LatLon DBF: %s", latlon_dbf)

    latlon = load_latlon_lookup(latlon_dbf)

    sup_url = os.environ.get("SUPABASE_URL")
    sup_key = (
        os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )
    if not sup_url or not sup_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_KEY required in env")
    db = create_client(sup_url, sup_key)

    # Stream parcel.dbf row-by-row to avoid loading 531K rows at once.
    # dbfread's DBF iterator lazily streams.
    logger.info("Streaming parcel.dbf...")
    total_read = 0
    total_kept = 0
    total_upserted = 0
    total_missing_coords = 0
    total_bbox_skipped = 0
    batch: list[dict] = []

    for parcel_row in DBF(str(parcel_dbf), encoding="utf-8", char_decode_errors="ignore"):
        total_read += 1
        if total_read % 50000 == 0:
            logger.info(
                "  read %d (kept %d, upserted %d, missing_coords %d)",
                total_read, total_kept, total_upserted, total_missing_coords,
            )
        row = build_property_row(parcel_row, latlon, args.county_id)
        if not row:
            continue
        total_kept += 1
        if row["latitude"] is None:
            total_missing_coords += 1
        batch.append(row)

        if len(batch) >= args.batch_size:
            upsert_batch(db, batch)
            total_upserted += len(batch)
            batch = []
        if args.limit and total_kept >= args.limit:
            break

    if batch:
        upsert_batch(db, batch)
        total_upserted += len(batch)

    logger.info(
        "DONE. parcel_read=%d, residential_kept=%d, upserted=%d, "
        "missing_centroid=%d",
        total_read, total_kept, total_upserted, total_missing_coords,
    )


if __name__ == "__main__":
    main()
