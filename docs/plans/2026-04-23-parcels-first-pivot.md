# Parcels-First Architecture Pivot

**Date**: 2026-04-23
**Status**: Planned, execution starting Phase 1

## Motivation

Current permits-first pipeline finds a house only if it has a filed HVAC permit. Houses with their original HVAC (built 2005, still on original system) are invisible — yet those are exactly the door-knock targets. Pivot: every residential parcel becomes a tracked property; permits overlay to refine the HVAC-age estimate. Residential parcels with no HVAC permit AND year_built ≥ 15 years ago are the richest lead tier.

## Phase 0 — Discovery (DONE)

**HCPAO parcel dataset** — https://downloads.hcpafl.org
- Filename: `parcel_{MM_DD_YYYY}.zip` (~181MB, weekly updates)
- Format: ESRI shapefile + ancillary DBFs (NOT CSV)
- 531,111 rows total; **450,826 are residential**
- Companion: `LatLon_Table_{date}.zip` (7MB, 540,791 rows, WGS84 centroids keyed by FOLIO)

**Key fields** (from official `_Documentation.doc`):
| Field | Type | Meaning |
|---|---|---|
| `FOLIO` | C(10) | 10-digit parcel ID — our new `parcel_number` PK |
| `DOR_C` | C(4) | Florida DOR use code, zero-padded |
| `OWNER` | C(75) | Owner name (no split first/last) |
| `SITE_ADDR, SITE_CITY, SITE_ZIP` | | Situs address |
| `ACT` | N | Actual year built |
| `HEAT_AR` | N | Heated sq ft (living area) |
| `JUST` | N | Assessed market value |
| `tBEDS, tBATHS, tSTORIES` | N | Counts |
| `BASE` | N | Homestead year; `0` = rental/non-homestead |

**Residential filter** (`DOR_C IN`):
- `'0100'` SFR (355,352) | `'0102'` SFR+MH
- `'0106'` Townhouse/Villa (39,671) | `'0111'` New Res Permit
- `'0200'` Mobile Home (13,572)
- `'0400'` Condominium (39,843) | `'0403'` Condo Apt | `'0408'` MH Condo
- `'0500'` Co-op | `'0508'` MH Co-op

**Current DB** (migrations up to 033):
- `properties.parcel_number` exists but is nullable and unindexed. Will become primary join key.
- `properties.normalized_address` is currently UNIQUE (county_id, normalized_address). Keep the column, drop the unique constraint (or move it to soft/non-unique).
- `leads.permit_id` is NOT NULL but marked DEPRECATED in migration 012. Must make nullable for parcel-first records.
- `leads.property_id` is UNIQUE already (migration 021). Good.
- RLS uses escape-hatch for anon key — unchanged.

**Rendering**: 400K pins can't all ship to the browser. Plan is bbox viewport-fetch + Mapbox `supercluster` (not the DOM-based leaflet.markercluster already in package.json, which maxes out ~50K).

## Hard requirements

1. HCFL only (no multi-county churn).
2. Residential only (DOR_C filter above).
3. Keep existing Map/List/Plan pages, FilterBar, DetailSheet, status machine, GHL. Incremental frontend changes only.
4. Scoring: age = `today - COALESCE(most_recent_hvac_date::year, year_built)`. Tier: HOT≥15, WARM≥10, COOL≥5, COLD<5.
5. Geocoder uses HCPAO lat/lng first, US Census fallback (now rare).
6. Out-of-bbox filter on any Census-sourced coordinates.

## Phased Rollout

Each phase is independently shippable and testable. Audit end-to-end on NEWBERRY / SUMMER SPRINGS / PANTHER TRACE / CATTAIL SHORE subdivisions at the end of each phase.

---

### Phase 1 — Schema migration (parcel-first fields)

**Goal**: Expand `properties` to hold HCPAO fields. Relax constraints that block parcel-first records.

**Files to create**:
- `database/migrations/034_parcels_first_properties.sql`

**What it does**:
1. `ALTER TABLE properties ADD COLUMN IF NOT EXISTS folio TEXT` — HCPAO FOLIO (10-digit). Distinct from the pre-existing `parcel_number` which was free-form. Populate `parcel_number = folio` during load for backwards compat.
2. `ADD COLUMN IF NOT EXISTS dor_code TEXT` (e.g., `'0100'`)
3. `ADD COLUMN IF NOT EXISTS heated_sqft INTEGER` (from HEAT_AR)
4. `ADD COLUMN IF NOT EXISTS bedrooms_count INTEGER, bathrooms_count NUMERIC, stories_count INTEGER, units_count INTEGER`
5. `ADD COLUMN IF NOT EXISTS homestead_year INTEGER` (from BASE; 0 → NULL, else the year homestead was approved)
6. `ADD COLUMN IF NOT EXISTS owner_occupied BOOLEAN` (computed: `homestead_year > 0`)
7. `ADD COLUMN IF NOT EXISTS last_sale_date DATE, last_sale_amount NUMERIC`
8. `ADD COLUMN IF NOT EXISTS is_residential BOOLEAN NOT NULL DEFAULT false` — for fast filtering
9. `ADD COLUMN IF NOT EXISTS source TEXT` — `'hcpao_parcel'` / `'permit_derived'` / `'legacy'`
10. Create `CREATE UNIQUE INDEX properties_folio_unique ON properties (county_id, folio) WHERE folio IS NOT NULL` — parcel-keyed dedup.
11. Create `CREATE INDEX properties_is_residential ON properties (is_residential, lead_tier) WHERE is_residential`.
12. Create `CREATE INDEX properties_lat_lng ON properties (latitude, longitude) WHERE latitude IS NOT NULL AND is_residential` — for bbox queries.
13. `ALTER TABLE leads ALTER COLUMN permit_id DROP NOT NULL` — allow leads with no seed permit.
14. Trigger: `properties_touch_updated_at` BEFORE UPDATE (currently missing, per migration 033 audit).

**Verification**:
- `SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name='properties' AND column_name IN ('folio','dor_code','is_residential','owner_occupied','source')` returns the new columns.
- `SELECT pg_get_indexdef(indexrelid) FROM pg_index WHERE indrelid='properties'::regclass AND indexrelid IN (SELECT oid FROM pg_class WHERE relname LIKE 'properties_folio%')` shows the new unique index.
- `INSERT INTO leads(county_id, property_id, lead_status) VALUES (...)` without permit_id succeeds.

**Anti-patterns**:
- DO NOT drop the existing `(county_id, normalized_address)` unique index in this migration — existing data depends on it. Dropping happens in Phase 3 after migration completes.
- DO NOT add `ON DELETE CASCADE` anywhere new. Existing cascades are enough.
- DO NOT introduce `updated_at` auto-expression on properties that would break existing backend writes that manually set it.

---

### Phase 2 — HCPAO loader script

**Goal**: Download latest HCPAO parcel + latlng files, filter to residential, bulk-insert into `properties`. Idempotent (re-runnable weekly).

**Files to create**:
- `backend/scripts/load_hcpao_parcels.py`
- Add `dbfread>=2.0.7` to `backend/requirements.txt`

**What it does**:
1. Fetch https://downloads.hcpafl.org/ directory (ASP.NET postback — use existing pattern from `hcfl_legacy_scraper.py` for session + csrf token)
2. Parse the page for the newest `parcel_YYYY_MM_DD.zip` and matching `LatLon_Table_YYYY_MM_DD.zip`
3. Download both to `/tmp/hcpao_cache/` (skip if already present)
4. Unzip, read `parcel.dbf` via `dbfread` — stream row-by-row (don't load 531K rows into memory at once)
5. Filter: `DOR_C in RESIDENTIAL_DOR_CODES`
6. Build lookup dict from `LatLon_Table.dbf` keyed by FOLIO → (lat, lng)
7. For each residential row, construct a property upsert payload:
   - folio, parcel_number=folio, dor_code=DOR_C, year_built=ACT
   - heated_sqft=HEAT_AR, total_property_value=JUST, land_value=LAND, improved_value=BLDG
   - bedrooms_count=tBEDS, bathrooms_count=tBATHS, stories_count=tSTORIES, units_count=tUNITS
   - owner_name=OWNER, homestead_year=BASE if BASE>0 else NULL, owner_occupied=(BASE>0)
   - last_sale_date=S_DATE, last_sale_amount=S_AMT
   - normalized_address = AddressNormalizer.normalize(SITE_ADDR)
   - city=SITE_CITY, zip_code=SITE_ZIP
   - latitude/longitude from LatLon lookup (filter bbox: 27.5–28.2, -82.9 to -82.0)
   - is_residential=true, source='hcpao_parcel', county_id=HCFL_COUNTY_ID
8. Bulk upsert in batches of 500 via `on_conflict='county_id,folio'`
9. At end: `UPDATE properties SET is_residential=false WHERE folio IS NULL` (existing permit-derived rows)
10. Log: total parcels read, residential kept, bbox-filtered out, upserted, updated, inserted.

**Verification**:
- `SELECT COUNT(*) FROM properties WHERE is_residential` ≈ 450K
- `SELECT COUNT(*) FROM properties WHERE source='hcpao_parcel'` matches
- Pick 5 random FOLIOs, compare DB row to HCPAO's public Property Search UI (https://www.hcpafl.org/PropertySearch)
- For the 4 audit streets (NEWBERRY, SUMMER SPRINGS, PANTHER TRACE, CATTAIL SHORE), count distinct FOLIOs — should match rough house counts visible in Google Maps / HCPAO parcel map

**Anti-patterns**:
- DO NOT use pandas (will OOM on 500K rows with 47 columns)
- DO NOT compute polygon centroids from `.shp` — `LatLon_Table.dbf` already has WGS84 points, don't duplicate work
- DO NOT fetch owner mail addresses (`ADDR_1/2, CITY, STATE, ZIP`) — those are the owner's mailing address, not the property situs. Use `SITE_*` only.

---

### Phase 3 — Permit-to-parcel linkage

**Goal**: Re-link existing 41K permits (22K legacy + 19K Accela) to the new parcel-sourced properties. Delete the phantom "HILLSBOROUGH COUNTY FL" property.

**Files to create**:
- `backend/scripts/relink_permits_to_parcels.py`
- `database/migrations/035_drop_normalized_address_unique.sql`

**What `035` does**:
- `DROP INDEX properties_county_id_normalized_address_key` (the old unique constraint)
- Replace with non-unique composite `CREATE INDEX properties_normalized_address ON properties (county_id, normalized_address) WHERE normalized_address IS NOT NULL`

**What `relink` does**:
1. `DELETE FROM leads WHERE property_id IN (SELECT id FROM properties WHERE normalized_address='HILLSBOROUGH COUNTY FL')`
2. `DELETE FROM properties WHERE normalized_address='HILLSBOROUGH COUNTY FL'` — removes the phantom bucket
3. For each permit (iterate via paginated select):
   - Try to match by `property_address` normalized → `properties.normalized_address` where `is_residential=true`
   - If match found: `UPDATE properties SET most_recent_hvac_permit_id=X, most_recent_hvac_date=GREATEST(current, new), total_hvac_permits=total_hvac_permits+1 WHERE id=X`
   - If no match: permit stays orphaned in `permits` table, won't drive any lead
4. For each matched property, recalculate hvac_age_years, lead_score, lead_tier using the **new** scoring (Phase 4 rule) — but Phase 3 uses the old rule (permit-based only) until Phase 4 ships. Document this sequencing.
5. Drop existing non-parcel properties that aren't needed: `DELETE FROM properties WHERE source IS NULL AND is_residential=false AND NOT EXISTS (SELECT 1 FROM leads WHERE property_id=properties.id)`. Keep permit-derived properties that already have a lead — those are user-visible.

**Verification**:
- `SELECT COUNT(*) FROM permits WHERE property_address IS NOT NULL` vs count of permits with a matching property → linkage rate should be >80% (some permits have unaddressable records)
- Test address: find 5 permits for "7930 BAY POINTE DRIVE", verify they all link to the same parcel-sourced property row (not the old permit-derived one) and `total_hvac_permits=5+`
- `SELECT COUNT(*) FROM properties WHERE normalized_address='HILLSBOROUGH COUNTY FL'` = 0
- Properties count ≈ 450K + a few thousand unmatched-permit holdovers

**Anti-patterns**:
- DO NOT delete permits themselves — they're the historical record, keep all 41K
- DO NOT modify `properties.id` UUIDs — leads, GHL handoff, existing references depend on them
- DO NOT run relink concurrently with geocoder or scraper

---

### Phase 4 — Scoring rewrite (year_built fallback)

**Goal**: Compute HVAC age from year_built when no permit exists. Re-tier all residential properties.

**Files to modify**:
- `backend/app/services/property_aggregator.py` — add `effective_hvac_year()` method
- `backend/app/routers/properties.py` (or wherever scoring is surfaced) — hook to re-score

**Files to create**:
- `backend/scripts/retier_all_residentials.py` — one-shot re-tier + lead-create where missing

**What the aggregator change does**:
```python
def effective_hvac_year(self, property_row) -> int | None:
    """Return the year representing the age of the current HVAC system.
    Prefer most-recent HVAC permit; fall back to year_built."""
    if property_row.get("most_recent_hvac_date"):
        return int(property_row["most_recent_hvac_date"][:4])
    if property_row.get("year_built"):
        return property_row["year_built"]
    return None
```

`calculate_hvac_age()` becomes: `current_year - effective_hvac_year()` if available, else None. `determine_lead_tier()` unchanged (thresholds 15/10/5).

**What `retier_all_residentials.py` does**:
1. Paginate over all residential properties (is_residential=true)
2. For each: compute effective age, score, tier
3. UPDATE properties SET hvac_age_years, lead_score, lead_tier
4. For properties without a lead row, INSERT into leads (county_id, property_id, lead_status='NEW'). permit_id=NULL now that Phase 1 made it nullable.
5. For existing leads, UPDATE lead_tier/lead_score to match.

**Verification**:
- Distribution check: expected ~30% HOT (houses built pre-2010 with no replacement permit), ~30% WARM, ~20% COOL, ~20% COLD. Roughly.
- Pick 5 known addresses with no HVAC permit: their tier should match (today - year_built) bucketing
- A property with a 2020 HVAC permit and year_built=1985 should be COLD (based on 2020 permit), not HOT — permit wins
- Leads count ≈ residential properties count (nearly 1:1 post-retier)

**Anti-patterns**:
- DO NOT drop lead rows during retier — status machine state (KNOCKED_NO_ANSWER, INTERESTED) is preserved
- DO NOT recompute `hvac_age_years` at query time — persist in the column; recompute only when underlying data changes

---

### Phase 5 — Map viewport-fetch + Supercluster

**Goal**: Handle 450K pins without freezing browser. Bbox-fetch from API, cluster client-side with `supercluster`, render individual pins only at zoom ≥ 17.

**Files to create**:
- `frontend/src/hooks/useBboxProperties.js` — debounced fetcher by bbox + zoom
- `frontend/src/components/map/SuperclusterLayer.jsx` — custom Leaflet layer that owns a supercluster index

**Files to modify**:
- `frontend/package.json` — add `supercluster`. Remove unused `leaflet.markercluster`, `react-leaflet-cluster`.
- `frontend/src/pages/MapPage.jsx` — replace flat `CircleMarker` rendering with Supercluster layer + viewport fetch
- `backend/app/routers/leads.py` — add bbox/zoom query params to `GET /api/leads`. Filter by `properties.latitude BETWEEN :min_lat AND :max_lat AND properties.longitude BETWEEN :min_lng AND :max_lng`. Cap at 10,000 rows returned.

**What the backend change does**:
Add to `list_leads`:
- `bbox_ne_lat, bbox_ne_lng, bbox_sw_lat, bbox_sw_lng` query params
- If all 4 present, filter `properties.latitude BETWEEN bbox_sw_lat AND bbox_ne_lat AND properties.longitude BETWEEN bbox_sw_lng AND bbox_ne_lng`
- `limit` param still honored but capped at 10K
- New return field `truncated: true` if hit the cap

**What the frontend does**:
- `useBboxProperties` hook: `useMapEvents({ moveend, zoomend })` → debounced 250ms → `useLeads({ bbox, zoom })`
- Supercluster layer: rebuild index on data change. On `moveend`, call `index.getClusters(bbox, Math.floor(zoom))`. Cluster markers use DivIcon with count; individual pins use existing `CircleMarker`.
- At zoom ≥ 17, call supercluster with zoom=20 (effectively disables clustering for visible viewport).

**Verification**:
- Zoom to a subdivision (like Newberry Grove Loop area), expect ~50-300 individual pins, all placed on actual houses
- Zoom out to county view, expect 5-50 cluster markers, not 450K dots
- Pan should debounce-fetch; no more than 1 fetch per 250ms during continuous pan
- Lighthouse perf score unchanged

**Anti-patterns**:
- DO NOT use `leaflet.markercluster` — already proven it maxes out at ~50K
- DO NOT ship all 450K coords down to browser even once — bbox-fetch or bust
- DO NOT compute clusters server-side in Python — Supercluster's JS implementation is fast enough and keeps state on the client

---

### Phase 6 — Filter/list UI updates

**Goal**: FilterBar and ListPage work cleanly against the new data shape. Add filters that matter for the new world.

**Files to modify**:
- `frontend/src/components/shared/FilterBar.jsx` — add `ownerOccupied`, `yearBuiltMin`, `hasPermitHistory` filters
- `frontend/src/api/leads.js` — pass the new params through
- `backend/app/routers/leads.py` — accept `owner_occupied=true/false`, `year_built_min`, `has_permit_history=true/false`
- `frontend/src/pages/ListPage.jsx` — add columns for year_built, owner_occupied, total_hvac_permits

**Verification**:
- Filter `ownerOccupied=true` → only homestead residences
- Filter `yearBuiltMin=1990` → older residences only
- Filter `hasPermitHistory=true` → only properties with ≥1 permit linked (edge cases: expensive recent replacements to avoid)
- ListPage shows 12K+ rows with virtual scroll; no render thrashing

**Anti-patterns**:
- DO NOT add filters that require server-side joins on new columns without indexes — add indexes in Phase 1 or a sub-migration here
- DO NOT replace existing filters — additive only

---

### Phase 7 — Cleanup & end-to-end verification

**Goal**: Prove the pivot on the 4 audit subdivisions. Document rollback.

**Tasks**:
1. Manual audit pass: NEWBERRY / SUMMER SPRINGS / PANTHER TRACE / CATTAIL SHORE
   - For each street, open the actual Riverview subdivision on Google Maps
   - In our app, filter by that street, compare pin count to visible house count
   - Pick 3 random houses per street, verify year_built, owner, tier make sense
2. Compare HOT count before/after pivot — expect 10-20× growth
3. Check WARM / COOL / COLD distribution is non-degenerate (not all in one bucket)
4. Run `backend/tests/` (pytest) — fix any regressions
5. Deploy backend (Railway), frontend (Vercel)
6. Write `docs/plans/2026-04-23-parcels-first-pivot-rollback.md` — SQL to rollback migrations + previous-version docker image for Railway

**Verification**:
- All 4 subdivision streets show a pin per house (visually in the map)
- HOT lead count for each street roughly matches "houses built 2005-2010" (should be most of Newberry Grove Loop)
- The phantom "HILLSBOROUGH COUNTY FL" is gone
- Out-of-county pins = 0 (post-HCPAO bbox filter)

---

## Risk Register

| Risk | Probability | Mitigation |
|---|---|---|
| HCPAO file schema drifts | Low | Documentation stable since 2017-07-25; loader uses column names not positions |
| 450K rows slow Supabase queries | Medium | Indexes on lat/lng, is_residential, lead_tier. Bbox filter for map. List page paginates. |
| Frontend supercluster flicker | Medium | React Query `keepPreviousData`, stable cluster IDs. Debounce 250ms. |
| Phantom property deletion surprises someone | Low | It's already a garbage bucket with zero actionable use |
| Relink rate < 50% | Medium | Accept; permits stay in `permits` as historical record. Address normalization improves over time. |
| Supabase egress cost blowup | Low | Bbox-fetch caps at 10K rows; at 10K × 100 fetches/day × 10KB ≈ 10MB/day. Trivial. |
| Vercel build fails after new deps | Low | `supercluster` is pure JS, no native deps |
| Railway job worker break from schema migration | Low | Additive-only in Phase 1; nothing removed |
| Homestead/owner_occupied data is stale | Known | HCPAO updates weekly. Acceptable accuracy for door-knock filter. |

---

## Testing strategy

Each phase has its own tests under `backend/tests/`. Specifically:

- `test_hcpao_loader.py` (Phase 2) — mock the zip fetch, verify residential filter, verify row count, verify lat/lng merge
- `test_permit_parcel_relink.py` (Phase 3) — fixtures with known address, verify linkage for happy + unhappy paths
- `test_effective_hvac_year.py` (Phase 4) — permit beats year_built; missing both = None; permit NULL + year_built present = year_built used
- `test_bbox_filter.py` (Phase 5) — integration test against a test Supabase schema
- `test_filterbar_residential_filters.py` (Phase 6) — vitest/RTL

End-to-end in Phase 7: the 4 subdivisions.

## Files reference (quick index)

### New files
- `backend/scripts/load_hcpao_parcels.py` (Phase 2)
- `backend/scripts/relink_permits_to_parcels.py` (Phase 3)
- `backend/scripts/retier_all_residentials.py` (Phase 4)
- `database/migrations/034_parcels_first_properties.sql` (Phase 1)
- `database/migrations/035_drop_normalized_address_unique.sql` (Phase 3)
- `frontend/src/hooks/useBboxProperties.js` (Phase 5)
- `frontend/src/components/map/SuperclusterLayer.jsx` (Phase 5)
- `backend/tests/test_hcpao_loader.py` (Phase 2)
- `backend/tests/test_permit_parcel_relink.py` (Phase 3)
- `backend/tests/test_effective_hvac_year.py` (Phase 4)

### Modified files
- `backend/app/services/property_aggregator.py` (Phase 4)
- `backend/app/routers/leads.py` (Phase 5, 6)
- `backend/requirements.txt` (Phase 2 — add `dbfread`)
- `frontend/package.json` (Phase 5 — add `supercluster`, remove markercluster)
- `frontend/src/pages/MapPage.jsx` (Phase 5)
- `frontend/src/pages/ListPage.jsx` (Phase 6)
- `frontend/src/components/shared/FilterBar.jsx` (Phase 6)
- `frontend/src/api/leads.js` (Phase 5, 6)

## Rollback plan

Each migration has a paired rollback script in `database/rollback/`. Specifically:
- `rollback_034.sql` — drop new columns + indexes, add back `NOT NULL` to leads.permit_id
- `rollback_035.sql` — recreate `(county_id, normalized_address)` unique index (will fail if duplicates exist post-pivot; script flags the conflicts for manual resolution)

Git revert + Railway rollback to previous deploy image covers code changes.
