# HVAC Lead Generation Platform - Backend API

FastAPI backend for the HVAC Lead Generation platform with Accela API and Summit.AI CRM integration.

## Features

- **Multi-county permit pulling** with Accela Civic Platform V4 API
- **Adaptive rate limiting** (header-based dynamic throttling for Accela API)
- **Background job processing** (30-year historical pulls, automated incremental pulls)
- **Property-centric data model** with intelligent lead scoring (HOT/WARM/COOL/COLD tiers)
- **Automated scheduler** for daily incremental pulls
- **Automatic token refresh** (handles 15-minute expiration)
- **Property data enrichment** (parcels, owners, addresses from Accela)
- **Lead management** with batch selection and CRM sync
- **Summit.AI (HighLevel) CRM integration**
- **Encrypted credential storage** (Fernet encryption)
- **RESTful API** with automatic documentation (Swagger/ReDoc)

## Current Status

**V1 - Accela Integration (Production-Ready):**
- ✅ Accela Civic Platform V4 API integration validated (HCFL pilot)
- ✅ Header-based adaptive rate limiting prevents API suspension
- ✅ 30-year historical pull capability (rolling window: `current_year - 30`)
- ✅ Automated incremental pulls every 7 days (8-day window with 1-day overlap)
- ✅ Property aggregation with intelligent lead scoring (HOT/WARM/COOL/COLD tiers)
- ✅ Summit.AI CRM integration with deduplication

**Current Deployment:**
- 📊 **0 counties configured** (HCFL pilot deleted for statewide rebuild)
- 🎯 **~25-30 Florida Accela counties** ready for immediate configuration
- 🚧 **37-42 remaining counties** require V2 multi-platform support (see README.md Future Vision)

**Backend Production URL:** https://hvac-backend-production-11e6.up.railway.app

## Technology Stack

- **Framework:** FastAPI
- **Database:** Supabase (PostgreSQL)
- **External APIs:** Accela Civic Platform V4, Summit.AI (HighLevel)
- **Security:** Fernet encryption for credentials

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings and env vars
│   ├── database.py                # Supabase connection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── county.py              # County Pydantic models
│   │   ├── permit.py              # Permit Pydantic models
│   │   ├── lead.py                # Lead Pydantic models
│   │   ├── property.py            # Property Pydantic models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── counties.py            # County endpoints
│   │   ├── permits.py             # Permit endpoints
│   │   ├── leads.py               # Lead endpoints
│   │   ├── properties.py          # Property endpoints
│   │   ├── summit.py              # Summit.AI endpoints
│   │   ├── background_jobs.py     # Background job endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── accela_client.py       # Accela API integration
│   │   ├── rate_limiter.py        # Accela API rate limiting
│   │   ├── summit_client.py       # Summit.AI integration
│   │   ├── property_aggregator.py # Property aggregation & lead scoring
│   │   ├── scheduler.py           # Automated pull scheduler
│   │   ├── encryption.py          # Credential encryption
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── job_processor.py       # Background job processor
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output for your `.env` file.

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUMMIT_API_KEY=your-summit-api-key
SUMMIT_LOCATION_ID=your-summit-location-id
ENCRYPTION_KEY=your-generated-encryption-key

# Accela API Rate Limiting (Optional - defaults shown)
ACCELA_RATE_LIMIT_THRESHOLD=0.15              # 85% usage threshold
ACCELA_PAGINATION_DELAY_FALLBACK=0.5          # 500ms pagination fallback
ACCELA_ENRICHMENT_DELAY_FALLBACK=0.1          # 100ms enrichment fallback
ACCELA_MAX_RETRIES=3                          # Max 429 retry attempts
ACCELA_REQUEST_TIMEOUT=30.0                   # Request timeout (seconds)
```

### 4. Set Up Supabase Database

Run the SQL migrations in Supabase to create the required tables:

- `agencies`
- `counties`
- `permits`
- `leads`

(See `docs/plans/2025-11-28-hvac-lead-gen-design.md` for schema)

### 5. Run the Server

```bash
# Development mode (auto-reload)
uvicorn app.main:app --reload

# Or using Python directly
python -m app.main

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## API Endpoints

### Health Check

```
GET /api/health
```

**Comprehensive system health monitoring** for all components:

**Critical Priority:**
- ✅ Database (Supabase connectivity, query response time)
- ✅ Encryption (Fernet encryption/decryption verification)
- ✅ Configuration (Required environment variables validation)

**High Priority:**
- 🔄 Job Processor (Background worker status, pending jobs count)

**Medium Priority:**
- 🌐 External APIs (Accela, Summit.AI connectivity - cached)
- 🏗️ Infrastructure (Vercel frontend, Railway backend health - cached)

**Low Priority:**
- 🔧 Network (Internet connectivity - cached)

**Response Format:**
```json
{
  "status": "healthy|degraded|down",
  "uptime_seconds": 86400,
  "components": {
    "database": { "status": "healthy", "priority": "critical", "message": "...", "response_time_ms": 45 },
    "encryption": { "status": "healthy", "priority": "critical", "message": "..." },
    "configuration": { "status": "healthy", "priority": "critical", "message": "..." },
    "job_processor": { "status": "healthy", "priority": "high", "message": "..." },
    "accela_api": { "status": "unknown", "priority": "medium", "message": "...", "last_checked": "..." },
    "summit_api": { "status": "unknown", "priority": "medium", "message": "...", "last_checked": "..." },
    "vercel_frontend": { "status": "healthy", "priority": "medium", "message": "...", "last_checked": "..." },
    "railway_backend": { "status": "healthy", "priority": "medium", "message": "...", "last_checked": "..." }
  },
  "summary": {
    "total": 8,
    "healthy": 7,
    "degraded": 0,
    "down": 0,
    "unknown": 1
  }
}
```

**Hybrid Checking Strategy:**
- **Fast checks** (database, encryption, config, job processor): Run inline on every request
- **Slow checks** (external APIs, infrastructure): Cached and updated in background every 60 seconds

**Use Cases:**
- Kubernetes liveness/readiness probes
- Uptime monitoring (Pingdom, UptimeRobot, etc.)
- Load balancer health checks
- Automated alerting on degraded status

### County Management

```
POST   /api/counties                       - Create county with credentials
GET    /api/counties                       - List all counties
GET    /api/counties/{id}                  - Get county details
PUT    /api/counties/{id}                  - Update county
DELETE /api/counties/{id}                  - Delete county
POST   /api/counties/{id}/test             - Test Accela connection
POST   /api/counties/test-credentials      - Test credentials without saving
GET    /api/counties/{id}/rate-limit-stats - Get Accela API rate limit statistics
```

### Permit Operations

```
POST   /api/counties/{id}/pull-permits
       Body: { date_from, date_to, limit, status }
       - Pulls permits from Accela, filters for HVAC (Mechanical)
       - Enriches with addresses, owners, parcels
       - Stores full raw JSON

GET    /api/permits
       Query: county_id, date_from, date_to, limit, offset
       - List permits with filters

GET    /api/permits/{id}
       - Get single permit with full details
```

### Lead Management

```
GET    /api/leads
       Query: county_id, sync_status, limit, offset
       - List leads with filters

POST   /api/leads/create-from-permits
       Body: { permit_ids: [...] }
       - Convert selected permits to leads

PUT    /api/leads/{id}/notes
       Body: { notes: "..." }
       - Update lead notes

POST   /api/leads/sync-to-summit
       Body: { lead_ids: [...] }  # empty = sync all pending
       - Sync leads to Summit.AI CRM
```

### Summit.AI Integration

```
GET    /api/summit/config         - Get config (masked)
PUT    /api/summit/config         - Update config
POST   /api/summit/test           - Test connection
GET    /api/summit/sync-status    - Get sync status
```

### Background Jobs

```
POST   /api/background-jobs/counties/{id}/jobs
       Body: { job_type, parameters }
       - Create async background job (initial_pull, incremental_pull)
       - Prevents concurrent jobs per county

GET    /api/background-jobs/counties/{id}/jobs
       Query: status, limit
       - List jobs with real-time progress

GET    /api/background-jobs/jobs/{id}
       - Get detailed job status with progress tracking
       - Returns: permits_pulled, properties_created, leads_created
       - Returns: progress_percent, permits_per_second, estimated_completion_at

POST   /api/background-jobs/jobs/{id}/cancel
       - Cancel pending or running job (graceful, finishes current batch)

DELETE /api/background-jobs/jobs/{id}
       - Delete completed/failed job
```

## Background Job System

### Architecture

The backend uses a **PostgreSQL-based polling system** for background jobs - no external dependencies like Celery, Redis, or ARQ required.

**Components:**
- `JobProcessor` (`app/workers/job_processor.py`) - Polls `background_jobs` table every 5 seconds
- `PullScheduler` (`app/services/scheduler.py`) - Checks every hour for due incremental pulls
- `PropertyAggregator` (`app/services/property_aggregator.py`) - Processes permits into property records with lead scoring

Both services start automatically when FastAPI launches and run as background asyncio tasks.

### Job Types

#### 1. Initial Pull (30-Year Historical Pull)

**Purpose:** Pull 30 years of historical HVAC permits to build complete lead database

**Strategy:**
- Pulls oldest permits first (1995 → 2025) for best lead prioritization
- Processes year-by-year in batches of 1,000 permits
- Real-time progress tracking with ETA

**Example:**
```bash
curl -X POST http://localhost:8000/api/background-jobs/counties/{county_id}/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "initial_pull",
    "parameters": {
      "years": 30,
      "permit_type": "Building/Residential/Trade/Mechanical"
    }
  }'
```

**Progress Tracking:**
- `current_year`: Year being processed (e.g., 2015)
- `current_batch`: Batch number within year
- `permits_pulled`: Total permits fetched from Accela
- `permits_saved`: Unique permits saved to database
- `properties_created`: New property records created
- `properties_updated`: Existing properties updated
- `leads_created`: Qualified leads generated (HVAC age ≥5 years)
- `permits_per_second`: Processing rate
- `estimated_completion_at`: ETA timestamp

**Typical Performance:**
- ~10-20 permits/second (depending on Accela API latency)
- 30 years with 10,000 permits = ~10-15 minutes

#### 2. Incremental Pull (Automated Every 7 Days)

**Purpose:** Pull recent permits to catch new HVAC installations

**Strategy:**
- Pulls last 8 days of permits (1-day overlap with 7-day frequency ensures no gaps)
- Triggered manually or by automated scheduler

**Example:**
```bash
curl -X POST http://localhost:8000/api/background-jobs/counties/{county_id}/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "incremental_pull",
    "parameters": {
      "days_back": 8,
      "permit_type": "Building/Residential/Trade/Mechanical"
    }
  }'
```

**Automated Scheduling:**
The `PullScheduler` automatically creates incremental_pull jobs for counties with:
- `auto_pull_enabled = TRUE` in `county_pull_schedules`
- `incremental_pull_enabled = TRUE`
- `next_pull_at <= NOW()`
- `initial_pull_completed = TRUE` (in counties table)

Scheduler checks every hour and creates jobs for due counties, then reschedules for 7 days later.

### Error Handling & Retries

**Automatic Retry:**
- Jobs automatically retry up to 3 times on failure
- Each retry increments `retry_count`
- After 3 failures, job status = `failed` permanently

**Statuses:**
- `pending` - Waiting for processor to pick up
- `running` - Currently being processed
- `completed` - Successfully finished
- `failed` - Permanently failed after max retries
- `cancelled` - User-cancelled (graceful shutdown)

**Logging:**
- All job progress logged to backend console
- Detailed error messages stored in `error_message` field
- Full stack trace in `error_details` (JSON)

### Data Enrichment Pipeline

Each permit goes through this pipeline:

1. **Fetch from Accela API:** Get base permit data
2. **Enrich with Details:**
   - Addresses (primary address extracted)
   - Owners (primary owner extracted)
   - Parcels (year built, square footage, property value)
3. **Save to `permits` table** with full `raw_data` JSONB
4. **Property Aggregation:**
   - Normalize address (uppercase, no punctuation)
   - Find or create property record
   - Calculate HVAC age from `opened_date`
   - Calculate lead score (0-100) and tier (HOT/WARM/COOL/COLD)
   - Create lead if qualified (HVAC age ≥5 years)

### Monitoring Jobs

**Real-time Progress:**
```bash
# Watch job progress
curl http://localhost:8000/api/background-jobs/jobs/{job_id}
```

**Response includes:**
```json
{
  "id": "...",
  "status": "running",
  "progress_percent": 45,
  "current_year": 2010,
  "current_batch": 3,
  "permits_pulled": 4500,
  "permits_saved": 4250,
  "properties_created": 3800,
  "leads_created": 2100,
  "permits_per_second": 12.5,
  "estimated_completion_at": "2025-11-30T15:45:00Z",
  "elapsed_seconds": 360
}
```

**Cancel Long-Running Job:**
```bash
curl -X POST http://localhost:8000/api/background-jobs/jobs/{job_id}/cancel
```

## Important Implementation Details

### Accela API

**Critical:** The Accela API requires the `Authorization` header WITHOUT the "Bearer " prefix:

```python
headers = {
    "Authorization": access_token,  # NOT "Bearer {access_token}"
}
```

### Token Refresh

The `AccelaClient` automatically:
1. Checks token expiration before each API call
2. Refreshes the token if expired or expiring within 1 minute
3. Updates the database with new token and expiration time

### Rate Limiting

The `AccelaRateLimiter` implements **header-based adaptive throttling** to prevent 429 errors:

**Three-Layer Defense:**
1. **Proactive** - Monitors `x-ratelimit-remaining` header, pauses at 85% usage
2. **Reactive** - Handles 429 errors with wait-until-reset logic
3. **Fallback** - Uses fixed delays (500ms/100ms) when headers unavailable

**Key Features:**
- Dynamic throttling based on Accela's response headers
- Auto-retry on 429 errors (up to 3 attempts)
- Categorized delays for pagination vs enrichment requests
- Real-time monitoring via `/api/counties/{id}/rate-limit-stats`

See [CLAUDE.md](../CLAUDE.md#accela-api-rate-limiting) for complete documentation.

### HVAC Filtering

Permits are filtered at **API-level** using Accela's `type` parameter:

```python
# API request uses type filter
params = {
    "module": "Building",
    "type": "Building/Residential/Trade/Mechanical",  # Hierarchical type path
    "openedDateFrom": start_date,
    "openedDateTo": end_date
}
# Only HVAC permits returned - no client-side filtering needed
```

**Portal Display vs API Value:**
- Portal shows: "Residential Mechanical Trade Permit"
- API expects: `"Building/Residential/Trade/Mechanical"` (hierarchical path)

This API-level filtering is more efficient than pulling all Building permits and filtering client-side.

### Data Storage

All permit data is stored in `raw_data` JSONB field, ensuring no data loss. Extracted fields are also stored in structured columns for easy querying.

### Summit.AI Sync

The sync process:
1. Searches for existing contacts by phone/email
2. Updates existing or creates new contact
3. Adds tags: ["hvac-lead"]
4. Stores `summit_contact_id` in leads table
5. Updates sync status and timestamp

## Error Handling

All endpoints return standardized JSON responses:

```json
{
  "success": true/false,
  "data": { ... },
  "error": "error message or null"
}
```

## Security

- Credentials encrypted at rest using Fernet encryption
- CORS restricted to configured frontend origins
- API keys masked in responses
- Input validation with Pydantic models
- Connection testing before saving credentials

## Development

### Running Tests

```bash
pytest
```

### Code Style

```bash
black app/
flake8 app/
```

## Deployment

### Railway

1. Connect your GitHub repository
2. Set environment variables
3. Deploy command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Production URL:** https://hvac-backend-production-11e6.up.railway.app

### Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### "Encryption key error"
- Ensure you've generated and set `ENCRYPTION_KEY` in `.env`

### "Supabase connection failed"
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Check that tables exist in Supabase

### "Accela authentication failed"
- Verify credentials are correct
- Check that environment name matches (PROD, TEST, etc.)
- Ensure header format is correct (no "Bearer " prefix)

### "Summit.AI sync failed"
- Verify API key and location ID
- Check that contact data is complete (phone/email required)

## License

Proprietary - All rights reserved
