# HVAC Lead Generation Platform - Backend API

FastAPI backend for the HVAC Lead Generation platform with Accela API and Summit.AI CRM integration.

## Features

- Multi-county permit pulling with Accela Civic Platform V4 API
- Automatic token refresh (handles 15-minute expiration)
- Property data enrichment (parcels, owners, addresses)
- Lead management and batch selection
- Summit.AI (HighLevel) CRM integration
- Encrypted credential storage
- RESTful API with automatic documentation

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
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── counties.py            # County endpoints
│   │   ├── permits.py             # Permit endpoints
│   │   ├── leads.py               # Lead endpoints
│   │   ├── summit.py              # Summit.AI endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── accela_client.py       # Accela API integration
│   │   ├── summit_client.py       # Summit.AI integration
│   │   ├── encryption.py          # Credential encryption
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
GET /health
```

Returns server health status.

### County Management

```
POST   /api/counties              - Create county with credentials
GET    /api/counties              - List all counties
GET    /api/counties/{id}         - Get county details
PUT    /api/counties/{id}         - Update county
DELETE /api/counties/{id}         - Delete county
POST   /api/counties/{id}/test    - Test Accela connection
POST   /api/counties/test-credentials - Test credentials without saving
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

### HVAC Filtering

Permits are filtered for "Mechanical" type client-side after pulling from Accela:

```python
hvac_permits = [p for p in permits if "Mechanical" in p.get("type", {}).get("value", "")]
```

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

### Railway/Render

1. Connect your GitHub repository
2. Set environment variables
3. Deploy command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

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
