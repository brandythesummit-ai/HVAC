# HVAC Lead Generation Platform - Database Schema

This directory contains the PostgreSQL database schema for the HVAC Lead Generation platform, designed for deployment on **Supabase**.

## Schema Overview

The database uses a multi-tenant architecture with 9 core tables:

```
agencies (tenant/organization)
  └── counties (Accela API configurations)
        ├── permits (pulled from Accela)
        │     ├── leads (synced to The Summit.AI)
        │     └── properties (property-centric data)
        ├── pull_history (historical pull tracking)
        └── county_pull_schedules (automated pull schedules)
  ├── sync_config (sync settings)
  └── background_jobs (async job tracking)
```

### Core Tables

1. **agencies** - HVAC contractor organizations
   - Stores The Summit.AI CRM credentials
   - Top-level tenant entity

2. **counties** - County configurations with Accela API credentials
   - One county per Accela environment
   - Manages OAuth token refresh (15-minute expiration)
   - Tracks connection status and last pull time

3. **permits** - HVAC permits pulled from Accela
   - Stores complete raw JSON from Accela API
   - Enriched with property data (parcels, owners, addresses)
   - Unique constraint on (county_id, accela_record_id)

4. **leads** - Leads created from permits for CRM sync
   - Tracks sync status to The Summit.AI
   - Stores Summit contact ID after successful sync
   - Manages error messages for failed syncs

5. **sync_config** - Sync configuration per agency
   - Currently supports manual mode
   - Designed for future scheduled/realtime modes

6. **properties** - Property-centric data model with intelligent lead scoring
   - **Address Normalization:** Uses `normalized_address` (uppercase, no punctuation) to match multiple permits to the same property
   - **HVAC Age Tracking:** Automatically calculates `hvac_age_years` from most recent HVAC permit date
   - **Lead Qualification:** Properties with HVAC age ≥5 years marked as `is_qualified = TRUE`
   - **Intelligent Scoring:** 0-100 lead score based on HVAC age, property value, and permit history
   - **Lead Tiers:** Automatic classification based on replacement urgency:
     - **HOT (80-100):** 15-20+ years old - Replacement imminent, highest priority
     - **WARM (60-75):** 10-15 years old - Maintenance + potential replacement soon
     - **COOL (40-55):** 5-10 years old - Maintenance focus, monitor for future
     - **COLD (0-35):** <5 years old - Not qualified, too new for outreach
   - **Denormalized Owner Data:** Stores most recent owner info for fast queries without joins
   - **Property Metadata:** Year built, lot size, total value, bedrooms, bathrooms
   - **Statistics:** Tracks `total_hvac_permits` counter for property activity level
   - **Use Case:** Enables targeting high-value properties with aging HVAC systems for replacement campaigns

7. **background_jobs** - Background task tracking
   - Tracks async job execution (historical pulls, etc.)
   - Stores job type, status, start/completion times
   - Manages error messages for failed jobs

8. **pull_history** - Historical permit pull tracking
   - Records each permit pull operation
   - Tracks date ranges, totals pulled, HVAC permits saved
   - Useful for audit trail and analytics

9. **county_pull_schedules** - Automated pull scheduling
   - Configures automated permit pulls per county
   - Supports daily, weekly, monthly schedules
   - Tracks last run and next scheduled run times

## Directory Structure

```
database/
├── migrations/
│   ├── 001_create_agencies.sql       # Agencies table
│   ├── 002_create_counties.sql       # Counties table with Accela config
│   ├── 003_create_permits.sql        # Permits with property data
│   ├── 004_create_leads.sql          # Leads with sync status
│   ├── 005_create_sync_config.sql    # Sync configuration
│   └── 006_create_indexes.sql        # Performance indexes
├── seed.sql                          # Sample data for testing
└── README.md                         # This file
```

## Setup Instructions

### Option 1: Supabase Dashboard (Recommended)

1. **Create a new Supabase project:**
   - Go to https://supabase.com/dashboard
   - Click "New Project"
   - Enter project name, database password, and region
   - Wait for provisioning (1-2 minutes)

2. **Run migrations:**
   - Open the SQL Editor in Supabase Dashboard
   - Copy and paste each migration file in order (001 → 006)
   - Click "Run" for each migration
   - Verify success (no errors)

3. **Seed test data (optional):**
   - Copy and paste `seed.sql` into SQL Editor
   - Click "Run"
   - Verify data in Table Editor

### Option 2: Supabase CLI

1. **Install Supabase CLI:**
   ```bash
   npm install -g supabase
   ```

2. **Login to Supabase:**
   ```bash
   supabase login
   ```

3. **Link to your project:**
   ```bash
   supabase link --project-ref <your-project-ref>
   ```

4. **Run migrations:**
   ```bash
   # Run all migrations in order
   for file in database/migrations/*.sql; do
     supabase db push --file "$file"
   done
   ```

5. **Seed test data:**
   ```bash
   supabase db push --file database/seed.sql
   ```

### Option 3: Direct PostgreSQL Connection

1. **Get connection string from Supabase:**
   - Settings → Database → Connection String
   - Copy the URI (use "Session mode" for migrations)

2. **Run migrations with psql:**
   ```bash
   # Set connection string
   export DATABASE_URL="postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"

   # Run migrations
   psql $DATABASE_URL -f database/migrations/001_create_agencies.sql
   psql $DATABASE_URL -f database/migrations/002_create_counties.sql
   psql $DATABASE_URL -f database/migrations/003_create_permits.sql
   psql $DATABASE_URL -f database/migrations/004_create_leads.sql
   psql $DATABASE_URL -f database/migrations/005_create_sync_config.sql
   psql $DATABASE_URL -f database/migrations/006_create_indexes.sql

   # Seed data
   psql $DATABASE_URL -f database/seed.sql
   ```

## Key Features

### Cascading Deletes
All foreign keys use `ON DELETE CASCADE` to maintain referential integrity:
- Deleting an agency removes all counties, permits, leads, and configs
- Deleting a county removes all permits and leads
- Deleting a permit removes the associated lead

### Indexes for Performance
Optimized indexes for common query patterns:
- County filtering: `idx_counties_agency_id`, `idx_counties_status`
- Permit filtering: `idx_permits_county_id`, `idx_permits_opened_date`
- Lead filtering: `idx_leads_summit_sync_status`, `idx_leads_county_id`
- Composite: `idx_permits_county_date`, `idx_leads_county_status`
- JSONB: `idx_permits_raw_data_gin` for JSON queries

### JSONB Storage
The `permits.raw_data` column stores the complete permit JSON from Accela:
- Ensures no data is lost during enrichment
- Allows flexible querying with GIN index
- Future-proof for schema changes

### Token Management
The `counties` table handles Accela's 15-minute token expiration:
- `accela_access_token` - Current OAuth token
- `token_expires_at` - Expiration timestamp
- Backend checks before each API call and refreshes if needed

## Security Notes

### Credential Encryption
The following columns will be encrypted by the backend:
- `agencies.summit_api_key`
- `counties.accela_app_secret`
- `counties.accela_access_token`

**Important:** The SQL schema does NOT handle encryption. The backend application (FastAPI) must encrypt these values before storage and decrypt on retrieval.

### Recommended: Supabase Row Level Security (RLS)

After migrations, enable RLS for production:

```sql
-- Enable RLS on all tables
ALTER TABLE agencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE counties ENABLE ROW LEVEL SECURITY;
ALTER TABLE permits ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE background_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pull_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE county_pull_schedules ENABLE ROW LEVEL SECURITY;

-- Example policy: Users can only see their own agency's data
CREATE POLICY "Users can view own agency" ON agencies
  FOR SELECT USING (auth.uid() = user_id);  -- Adjust based on your auth setup
```

## Test Data Overview

The `seed.sql` file creates:
- **1 Agency:** "Test HVAC Agency"
- **2 Counties:** Orange County (connected), Los Angeles County (disconnected)
- **5 Permits:** 4 from Orange County, 1 from LA County
- **5 Leads:** Various sync statuses (synced, pending, failed)
- **1 Sync Config:** Manual mode

### Sample Queries

```sql
-- View all permits with owner info
SELECT
  c.name AS county,
  p.accela_record_id,
  p.permit_type,
  p.opened_date,
  p.property_address,
  p.owner_name,
  p.job_value
FROM permits p
JOIN counties c ON p.county_id = c.id
ORDER BY p.opened_date DESC;

-- View leads by sync status
SELECT
  l.summit_sync_status,
  COUNT(*) AS count
FROM leads l
GROUP BY l.summit_sync_status;

-- Find high-value pending leads
SELECT
  p.owner_name,
  p.property_address,
  p.job_value,
  l.notes
FROM leads l
JOIN permits p ON l.permit_id = p.id
WHERE l.summit_sync_status = 'pending'
  AND p.job_value > 10000
ORDER BY p.job_value DESC;

-- Properties: Find HOT tier leads (HVAC 15+ years old)
SELECT
  normalized_address,
  owner_name,
  owner_phone,
  hvac_age_years,
  lead_score,
  lead_tier,
  most_recent_hvac_date,
  total_property_value,
  total_hvac_permits
FROM properties
WHERE lead_tier = 'HOT'
  AND is_qualified = TRUE
ORDER BY lead_score DESC, total_property_value DESC
LIMIT 50;

-- Properties: Score distribution by tier
SELECT
  lead_tier,
  COUNT(*) AS count,
  AVG(hvac_age_years) AS avg_hvac_age,
  AVG(total_property_value) AS avg_property_value,
  AVG(lead_score) AS avg_score
FROM properties
WHERE is_qualified = TRUE
GROUP BY lead_tier
ORDER BY CASE lead_tier
  WHEN 'HOT' THEN 1
  WHEN 'WARM' THEN 2
  WHEN 'COOL' THEN 3
  WHEN 'COLD' THEN 4
END;

-- Properties: Multi-permit properties (high activity)
SELECT
  normalized_address,
  owner_name,
  total_hvac_permits,
  hvac_age_years,
  lead_tier,
  total_property_value
FROM properties
WHERE total_hvac_permits > 1
  AND is_qualified = TRUE
ORDER BY total_hvac_permits DESC, lead_score DESC;
```

## Backend Integration

### Connection from FastAPI

```python
# Example using SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### Environment Variables

```bash
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=[ANON-KEY]
SUPABASE_SERVICE_KEY=[SERVICE-ROLE-KEY]  # For server-side operations
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres
```

## Troubleshooting

### Error: "uuid-ossp extension not found"
- Run in SQL Editor: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`
- Supabase enables this by default, but may need manual activation

### Error: "relation already exists"
- Drop tables and re-run: `DROP TABLE IF EXISTS leads, permits, sync_config, counties, agencies CASCADE;`
- Or use `IF NOT EXISTS` (already included in migrations)

### Slow queries
- Check if indexes were created: `\di` in psql or Table Editor → Indexes
- Re-run `006_create_indexes.sql` if missing

### Seed data not showing
- Verify migrations ran successfully first
- Check for foreign key constraint errors
- Run seed.sql again (it truncates tables first)

## Migration History

| Migration | Description | Date |
|-----------|-------------|------|
| 001 | Create agencies table | 2025-11-28 |
| 002 | Create counties table | 2025-11-28 |
| 003 | Create permits table | 2025-11-28 |
| 004 | Create leads table | 2025-11-28 |
| 005 | Create sync_config table | 2025-11-28 |
| 006 | Create indexes (initial) | 2025-11-28 |
| 006_rename | Rename summit_api_key column | 2025-11-28 |
| 008 | Add global Accela settings | 2025-11-28 |
| 009 | Add county OAuth refresh tokens | 2025-11-28 |
| 010 | **Create properties table** (property-centric model with lead scoring) | 2025-11-29 |
| 011 | **Create background_jobs table** (async job tracking) | 2025-11-29 |
| 012 | Modify leads table structure | 2025-11-29 |
| 013 | **Create pull_history table** (audit trail for permit pulls) | 2025-11-29 |
| 014 | **Create county_pull_schedules table** (automated scheduling) | 2025-11-29 |
| 015 | Alter counties status field | 2025-11-29 |

## Next Steps

1. **Run migrations** in your Supabase project
2. **Seed test data** to verify schema
3. **Configure backend** with database connection
4. **Test API endpoints** with sample data
5. **Enable RLS** for production security
6. **Set up backups** in Supabase dashboard

## Support

For issues or questions:
- Check Supabase logs in Dashboard → Logs
- Review migration files for schema details
- Test queries in SQL Editor
- Consult design doc: `docs/plans/2025-11-28-hvac-lead-gen-design.md`
