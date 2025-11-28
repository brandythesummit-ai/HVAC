# Quick Start Guide

## Installation & Setup

### 1. Install Dependencies
```bash
cd /Users/Brandy/projects/HVAC/backend
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
The `.env` file is already set up with a test configuration. For production, update:

```bash
# Edit .env and add your real credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
SUMMIT_API_KEY=your-summit-api-key
SUMMIT_LOCATION_ID=your-location-id
```

### 3. Start the Server
```bash
# Development mode (auto-reload)
uvicorn app.main:app --reload

# Or specify host/port
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start at: **http://localhost:8000**

## Quick Test

Run the test script:
```bash
python test_server.py
```

## API Documentation

Once the server is running:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

## Database Setup

You need to create these tables in Supabase:

### agencies
```sql
CREATE TABLE agencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    summit_api_key TEXT,
    summit_location_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### counties
```sql
CREATE TABLE counties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agency_id UUID REFERENCES agencies(id),
    name TEXT NOT NULL,
    accela_environment TEXT NOT NULL,
    accela_app_id TEXT NOT NULL,
    accela_app_secret TEXT NOT NULL,
    accela_access_token TEXT,
    token_expires_at TIMESTAMP,
    last_pull_at TIMESTAMP,
    status TEXT DEFAULT 'connected',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### permits
```sql
CREATE TABLE permits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_id UUID REFERENCES counties(id),
    accela_record_id TEXT UNIQUE NOT NULL,
    raw_data JSONB,
    permit_type TEXT,
    description TEXT,
    opened_date DATE,
    status TEXT,
    job_value NUMERIC,
    property_address TEXT,
    year_built INTEGER,
    square_footage INTEGER,
    property_value NUMERIC,
    bedrooms INTEGER,
    bathrooms NUMERIC,
    lot_size NUMERIC,
    owner_name TEXT,
    owner_phone TEXT,
    owner_email TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_permits_opened_date ON permits(opened_date);
CREATE INDEX idx_permits_county_id ON permits(county_id);
```

### leads
```sql
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    permit_id UUID REFERENCES permits(id),
    county_id UUID REFERENCES counties(id),
    summit_sync_status TEXT DEFAULT 'pending',
    summit_contact_id TEXT,
    summit_synced_at TIMESTAMP,
    sync_error_message TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_leads_sync_status ON leads(summit_sync_status);
CREATE INDEX idx_leads_county_id ON leads(county_id);
```

## Common Tasks

### Add a County
```bash
curl -X POST http://localhost:8000/api/counties \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sample County",
    "accela_environment": "TEST",
    "accela_app_id": "your-app-id",
    "accela_app_secret": "your-app-secret"
  }'
```

### Pull Permits
```bash
curl -X POST http://localhost:8000/api/counties/{county_id}/pull-permits \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": "2024-01-01",
    "date_to": "2024-12-31",
    "limit": 100,
    "status": "Finaled"
  }'
```

### Create Leads from Permits
```bash
curl -X POST http://localhost:8000/api/leads/create-from-permits \
  -H "Content-Type: application/json" \
  -d '{
    "permit_ids": ["permit-uuid-1", "permit-uuid-2"]
  }'
```

### Sync Leads to Summit.AI
```bash
curl -X POST http://localhost:8000/api/leads/sync-to-summit \
  -H "Content-Type: application/json" \
  -d '{
    "lead_ids": ["lead-uuid-1", "lead-uuid-2"]
  }'
```

## Troubleshooting

### Server won't start
- Check `.env` file exists and has valid encryption key
- Ensure Supabase URL and key are set
- Check logs for specific errors

### Accela API errors
- Verify credentials are correct
- Check environment name (PROD, TEST, etc.)
- Remember: NO "Bearer " prefix in Authorization header

### Database errors
- Ensure all tables are created in Supabase
- Check Supabase URL and key are correct
- Verify RLS (Row Level Security) policies if needed

## File Structure Reference

```
backend/
├── app/
│   ├── main.py              # FastAPI app & routes registration
│   ├── config.py            # Environment variables & settings
│   ├── database.py          # Supabase client
│   ├── models/              # Pydantic models for validation
│   │   ├── county.py
│   │   ├── permit.py
│   │   └── lead.py
│   ├── routers/             # API endpoint definitions
│   │   ├── counties.py      # County CRUD & testing
│   │   ├── permits.py       # Permit pulling & listing
│   │   ├── leads.py         # Lead creation & syncing
│   │   └── summit.py        # Summit.AI config & testing
│   └── services/            # External API clients
│       ├── accela_client.py # Accela API with auto-refresh
│       ├── summit_client.py # Summit.AI integration
│       └── encryption.py    # Credential encryption
├── requirements.txt
├── .env
├── test_server.py
└── README.md
```

## Next Steps

1. **Test with real Accela credentials** - Add a county and test connection
2. **Set up Supabase** - Create all required tables
3. **Pull sample permits** - Test the permit pulling workflow
4. **Configure Summit.AI** - Add API key and test sync
5. **Build frontend** - Connect React app to this API
