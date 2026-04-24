"""Import HVAC permits from a local Supabase backup into the live DB.

Background: our current DB's Accela pull stopped at 2021-12-31, but a
local backup at supabase-backups/hvac-lead-gen/data.sql holds 2021-2025
permits from a previous Supabase instance. This script parses the
backup's COPY block, remaps county_id to the current HCFL id, and
upserts into the current permits table. Idempotency is handled by the
composite UNIQUE on (county_id, source, source_permit_id).

Usage:
    source backend/venv/bin/activate
    python -m scripts.import_permit_backup
"""
import os
import re
import sys
import json
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

BACKUP_PATH = '/Users/Brandy/projects/supabase-backups/hvac-lead-gen/data.sql'
OLD_COUNTY_ID = '40c7d6e3-fd9e-48f1-9d3e-4d372d6001cc'
NEW_COUNTY_ID = '07e876b9-938e-4f53-b0dc-7bb9ce7e9cdd'

# Columns present in the current schema that we will populate.
# The backup has extra columns (custom_id, neighborhood, lot_size_sqft,
# land_value, improved_value, total_property_value, parcel_number,
# subdivision, legal_description) that no longer exist — dropped.
NEW_SCHEMA_COLS = (
    'county_id', 'accela_record_id', 'raw_data', 'permit_type',
    'description', 'opened_date', 'status', 'job_value',
    'property_address', 'year_built', 'square_footage', 'property_value',
    'bedrooms', 'bathrooms', 'lot_size', 'owner_name', 'owner_phone',
    'owner_email', 'source', 'source_permit_id',
)

INT_COLS = {'year_built', 'square_footage', 'bedrooms'}
FLOAT_COLS = {'job_value', 'property_value', 'bathrooms', 'lot_size'}


_COPY_ESCAPES = {
    't': '\t', 'n': '\n', 'r': '\r', 'b': '\b',
    'f': '\f', 'v': '\v', '\\': '\\',
}


def unescape_copy(val: str):
    """Reverse Postgres COPY TSV escapes in a single pass.

    Chained .replace() calls get the order wrong — e.g. \\\\t would
    turn into \t instead of a literal backslash followed by t — so
    we walk the string once and handle each escape atomically.
    """
    if val == '\\N':
        return None
    out = []
    i = 0
    n = len(val)
    while i < n:
        c = val[i]
        if c == '\\' and i + 1 < n:
            nxt = val[i + 1]
            if nxt in _COPY_ESCAPES:
                out.append(_COPY_ESCAPES[nxt])
                i += 2
                continue
        out.append(c)
        i += 1
    return ''.join(out)


def _coerce(col: str, raw: str):
    if raw is None:
        return None
    if col in INT_COLS:
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None
    if col in FLOAT_COLS:
        try:
            return float(raw)
        except (ValueError, TypeError):
            return None
    return raw


def iter_backup_permits(path: str):
    with open(path, 'r') as f:
        in_block = False
        cols = None
        for line in f:
            if line.startswith('COPY public.permits '):
                m = re.search(r'\((.+?)\) FROM stdin', line)
                cols = [c.strip() for c in m.group(1).split(',')]
                in_block = True
                continue
            if in_block:
                if line.startswith('\\.'):
                    break
                parts = line.rstrip('\n').split('\t')
                if parts[1] != OLD_COUNTY_ID:
                    continue
                row = {c: unescape_copy(v) for c, v in zip(cols, parts)}
                new_row = {
                    'county_id': NEW_COUNTY_ID,
                    'accela_record_id': row.get('accela_record_id'),
                    'raw_data': json.loads(row['raw_data']) if row.get('raw_data') else {},
                    'source': 'accela_api',
                    'source_permit_id': row.get('accela_record_id'),
                }
                for col in NEW_SCHEMA_COLS:
                    if col in new_row:
                        continue
                    new_row[col] = _coerce(col, row.get(col))
                yield new_row


def main():
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

    batch_size = 300
    total = inserted = errors = 0
    batch: list = []

    def flush():
        nonlocal inserted, errors
        if not batch:
            return
        try:
            res = sb.table('permits').upsert(
                batch,
                on_conflict='county_id,source,source_permit_id',
                ignore_duplicates=True,
            ).execute()
            inserted += len(res.data or [])
        except Exception as e:
            errors += 1
            print(f'!! batch error (total={total}): {e}', file=sys.stderr)
        batch.clear()

    for row in iter_backup_permits(BACKUP_PATH):
        batch.append(row)
        total += 1
        if len(batch) >= batch_size:
            flush()
            if total % 3000 == 0:
                print(f'  processed {total:,} rows · upserted {inserted:,} · errors {errors}')
    flush()

    print()
    print(f'Total backup rows processed: {total:,}')
    print(f'Upsert result rows returned: {inserted:,}')
    print(f'(Duplicates skipped silently by ON CONFLICT DO NOTHING)')
    print(f'Batch errors: {errors}')


if __name__ == '__main__':
    main()
