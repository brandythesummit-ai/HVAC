# Database Schema Quick Reference

## Entity Relationship Diagram

```
┌─────────────────────┐
│     agencies        │
│─────────────────────│
│ id (PK)             │
│ name                │
│ summit_api_key      │ (encrypted)
│ summit_location_id  │
│ created_at          │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────▼──────────┐         ┌─────────────────────┐
│  sync_config        │         │     counties        │
│─────────────────────│         │─────────────────────│
│ id (PK)             │         │ id (PK)             │
│ agency_id (FK)      │         │ agency_id (FK)      │
│ sync_mode           │         │ name                │
│ schedule_cron       │         │ accela_environment  │
│ is_active           │         │ accela_app_id       │
│ created_at          │         │ accela_app_secret   │ (encrypted)
└─────────────────────┘         │ accela_access_token │ (encrypted)
                                │ token_expires_at    │
                                │ last_pull_at        │
                                │ status              │
                                │ is_active           │
                                │ created_at          │
                                └──────────┬──────────┘
                                           │
                                           │ 1:N
                                           │
                                ┌──────────▼──────────┐
                                │      permits        │
                                │─────────────────────│
                                │ id (PK)             │
                                │ county_id (FK)      │
                                │ accela_record_id    │
                                │ raw_data (JSONB)    │
                                │ permit_type         │
                                │ description         │
                                │ opened_date         │
                                │ status              │
                                │ job_value           │
                                │ property_address    │
                                │ year_built          │
                                │ square_footage      │
                                │ property_value      │
                                │ bedrooms            │
                                │ bathrooms           │
                                │ lot_size            │
                                │ owner_name          │
                                │ owner_phone         │
                                │ owner_email         │
                                │ created_at          │
                                └──────────┬──────────┘
                                           │
                                           │ 1:1
                                           │
                                ┌──────────▼──────────┐
                                │       leads         │
                                │─────────────────────│
                                │ id (PK)             │
                                │ permit_id (FK)      │
                                │ county_id (FK)      │
                                │ summit_sync_status  │
                                │ summit_contact_id   │
                                │ summit_synced_at    │
                                │ sync_error_message  │
                                │ notes               │
                                │ created_at          │
                                └─────────────────────┘
```

## Table Summaries

### agencies
**Purpose:** Top-level tenant organizations (HVAC contractors)
**Key Fields:**
- `summit_api_key` - The Summit.AI CRM API credentials
- `summit_location_id` - The Summit.AI location/sub-account

### counties
**Purpose:** County configurations with Accela API credentials
**Key Fields:**
- `accela_app_id`, `accela_app_secret` - Accela OAuth credentials
- `accela_access_token` - Current token (expires every 15 minutes)
- `token_expires_at` - Token expiration timestamp
- `status` - Connection status (connected, disconnected, token_expired, error)

**Important:** Backend must check `token_expires_at` before each Accela API call and refresh if expired.

### permits
**Purpose:** HVAC permits pulled from Accela with enriched property data
**Key Fields:**
- `raw_data` - Complete permit JSON (preserves all original data)
- `accela_record_id` - Unique record ID from Accela
- Property fields: `year_built`, `square_footage`, `property_value`, etc.
- Owner fields: `owner_name`, `owner_phone`, `owner_email`

**Unique Constraint:** `(county_id, accela_record_id)` - Prevents duplicate permits

### leads
**Purpose:** Leads created from permits for syncing to The Summit.AI
**Key Fields:**
- `summit_sync_status` - Sync status: 'pending', 'synced', 'failed'
- `summit_contact_id` - Contact ID in The Summit.AI (after successful sync)
- `sync_error_message` - Error details if sync failed

### sync_config
**Purpose:** Sync configuration per agency
**Key Fields:**
- `sync_mode` - Currently 'manual', future: 'scheduled', 'realtime'
- `schedule_cron` - Cron expression for scheduled syncs (future feature)

## Indexes

### Performance Indexes
```sql
-- Counties
idx_counties_agency_id
idx_counties_status
idx_counties_is_active

-- Permits
idx_permits_county_id
idx_permits_opened_date
idx_permits_accela_record_id
idx_permits_permit_type
idx_permits_status
idx_permits_raw_data_gin (JSONB GIN index)

-- Leads
idx_leads_permit_id
idx_leads_county_id
idx_leads_summit_sync_status
idx_leads_summit_contact_id
idx_leads_created_at

-- Composite Indexes
idx_permits_county_date (county_id, opened_date DESC)
idx_leads_county_status (county_id, summit_sync_status)
```

## Cascading Deletes

```
DELETE agency
  → Deletes all counties
    → Deletes all permits
      → Deletes all leads
  → Deletes sync_config

DELETE county
  → Deletes all permits
    → Deletes all leads

DELETE permit
  → Deletes associated lead
```

## Data Types & Constraints

### UUID Primary Keys
All tables use UUID primary keys with `uuid_generate_v4()` default.

### Timestamps
All tables have `created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()`.

### Numeric Precision
- `job_value`: `NUMERIC(12, 2)` - Up to $999,999,999.99
- `property_value`: `NUMERIC(12, 2)` - Up to $999,999,999.99
- `bathrooms`: `NUMERIC(3, 1)` - Supports half baths (e.g., 2.5)
- `lot_size`: `NUMERIC(12, 2)` - Square feet or acres

### JSONB Storage
- `permits.raw_data` - Stores complete Accela permit JSON
- Indexed with GIN index for fast JSON queries
- Preserves all original data even if schema changes

## Common Queries

### Get all permits for a county with lead status
```sql
SELECT
  p.accela_record_id,
  p.permit_type,
  p.opened_date,
  p.owner_name,
  p.property_address,
  p.job_value,
  l.summit_sync_status,
  l.summit_contact_id
FROM permits p
LEFT JOIN leads l ON p.id = l.permit_id
WHERE p.county_id = 'county-uuid-here'
ORDER BY p.opened_date DESC;
```

### Get pending leads ready for sync
```sql
SELECT
  l.id AS lead_id,
  p.owner_name,
  p.owner_email,
  p.owner_phone,
  p.property_address,
  p.job_value,
  c.name AS county_name
FROM leads l
JOIN permits p ON l.permit_id = p.id
JOIN counties c ON l.county_id = c.id
WHERE l.summit_sync_status = 'pending'
  AND p.owner_email IS NOT NULL  -- Must have email for sync
ORDER BY p.job_value DESC;
```

### Get counties needing token refresh
```sql
SELECT
  id,
  name,
  status,
  token_expires_at
FROM counties
WHERE is_active = true
  AND (token_expires_at IS NULL OR token_expires_at < NOW())
ORDER BY name;
```

### Get sync statistics by county
```sql
SELECT
  c.name AS county,
  COUNT(l.id) AS total_leads,
  SUM(CASE WHEN l.summit_sync_status = 'synced' THEN 1 ELSE 0 END) AS synced,
  SUM(CASE WHEN l.summit_sync_status = 'pending' THEN 1 ELSE 0 END) AS pending,
  SUM(CASE WHEN l.summit_sync_status = 'failed' THEN 1 ELSE 0 END) AS failed
FROM counties c
LEFT JOIN leads l ON c.id = l.county_id
GROUP BY c.id, c.name
ORDER BY total_leads DESC;
```

## Security Considerations

### Encrypted Fields (handled by backend)
- `agencies.summit_api_key`
- `counties.accela_app_secret`
- `counties.accela_access_token`

### Row Level Security (RLS)
Enable RLS in production to restrict access:
```sql
ALTER TABLE agencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE counties ENABLE ROW LEVEL SECURITY;
ALTER TABLE permits ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_config ENABLE ROW LEVEL SECURITY;
```

### Recommended Policies
```sql
-- Example: Users can only access their own agency's data
CREATE POLICY "agency_isolation" ON permits
  FOR ALL USING (
    county_id IN (
      SELECT id FROM counties
      WHERE agency_id = current_setting('app.current_agency_id')::uuid
    )
  );
```

## Migration Order

**CRITICAL:** Run migrations in this exact order:

1. `001_create_agencies.sql` - Creates agencies table + UUID extension
2. `002_create_counties.sql` - Creates counties (references agencies)
3. `003_create_permits.sql` - Creates permits (references counties)
4. `004_create_leads.sql` - Creates leads (references permits + counties)
5. `005_create_sync_config.sql` - Creates sync_config (references agencies)
6. `006_create_indexes.sql` - Creates all indexes

Then optionally:
7. `seed.sql` - Loads test data (truncates all tables first)

## Verification Queries

After running migrations, verify schema:

```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('agencies', 'counties', 'permits', 'leads', 'sync_config')
ORDER BY table_name;

-- Check indexes exist
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;

-- Check foreign keys
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_name AS foreign_table_name,
  ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name, kcu.column_name;
```
