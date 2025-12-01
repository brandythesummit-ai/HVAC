# HVAC Lead Generation Platform - Design Document

**Date:** November 28, 2025
**Version:** 1.0

## Executive Summary

A lead generation platform for HVAC contractors that pulls permit data from county governments using the Accela API, enriches it with property information, and syncs qualified leads to The Summit.AI (white-label HighLevel CRM).

**Key Features:**
- Multi-county permit pulling with Accela API integration
- Automatic token refresh (15-minute expiration handling)
- Property data enrichment (age, sqft, value from Accela parcels API)
- Manual batch lead selection and review
- The Summit.AI CRM integration
- Multi-tenant architecture (future SaaS-ready)

---

## Technology Stack

**Frontend:**
- React + Vite
- TailwindCSS
- React Query
- Deployed on Vercel

**Backend:**
- Python 3.11+ FastAPI
- SQLAlchemy (ORM)
- Pydantic (validation)
- Deployed on Railway

**Database:**
- Supabase (PostgreSQL)

**External APIs:**
- Accela Civic Platform V4
- The Summit.AI (HighLevel) CRM

---

## System Architecture

```
Frontend (React/Vercel)
    ↓ REST API
Backend (FastAPI/Railway)
    ↓ SQL + API Calls
Database (Supabase) + Accela API + Summit.AI API
```

**Data Flow:**
1. User configures county with Accela credentials
2. User pulls permits (date range filters)
3. Backend calls Accela API (auto-refreshes token if needed)
4. Enriches permits with property data (parcels, owners, addresses)
5. Stores full raw JSON + extracted fields in database
6. User reviews leads in dashboard
7. User selects leads and syncs to The Summit.AI
8. Dashboard shows sync status

---

## Database Schema

### agencies
```sql
- id (uuid, pk)
- name (text)
- summit_api_key (text, encrypted)
- summit_location_id (text)
- created_at (timestamp)
```

### counties
```sql
- id (uuid, pk)
- agency_id (uuid, fk)
- name (text)
- accela_environment (text)
- accela_app_id (text)
- accela_app_secret (text, encrypted)
- accela_access_token (text, encrypted)
- token_expires_at (timestamp)
- last_pull_at (timestamp)
- status (text) -- 'connected', 'token_expired', 'error'
- is_active (boolean)
- created_at (timestamp)
```

### permits
```sql
- id (uuid, pk)
- county_id (uuid, fk)
- accela_record_id (text, unique)
- raw_data (jsonb) -- FULL permit JSON
- permit_type (text)
- description (text)
- opened_date (date, indexed)
- status (text)
- job_value (numeric)
- property_address (text)
- year_built (integer)
- square_footage (integer)
- property_value (numeric)
- bedrooms (integer)
- bathrooms (numeric)
- lot_size (numeric)
- owner_name (text)
- owner_phone (text)
- owner_email (text)
- created_at (timestamp)
```

### leads
```sql
- id (uuid, pk)
- permit_id (uuid, fk)
- county_id (uuid, fk)
- summit_sync_status (text) -- 'pending', 'synced', 'failed'
- summit_contact_id (text)
- summit_synced_at (timestamp)
- sync_error_message (text)
- notes (text)
- created_at (timestamp)
```

### sync_config
```sql
- id (uuid, pk)
- agency_id (uuid, fk)
- sync_mode (text) -- 'manual' (current), 'realtime', 'scheduled'
- is_active (boolean)
```

---

## API Endpoints

### County Management
```
POST   /api/counties              - Add county with credentials
GET    /api/counties              - List all counties
GET    /api/counties/{id}         - Get county details
PUT    /api/counties/{id}         - Update county
DELETE /api/counties/{id}         - Remove county
POST   /api/counties/{id}/test    - Test Accela connection
```

### Permit Operations
```
POST   /api/counties/{id}/pull-permits
  Body: { date_from, date_to, limit, status }
  → Pulls from Accela, enriches with parcels/owners/addresses

GET    /api/permits
  Query: county_id, date_from, date_to, limit, offset

GET    /api/permits/{id}
  → Full permit with raw JSON
```

### Lead Management
```
GET    /api/leads
  Query: county_id, sync_status, limit, offset

POST   /api/leads/create-from-permits
  Body: { permit_ids: [...] }

PUT    /api/leads/{id}/notes
  Body: { notes: "..." }

POST   /api/leads/sync-to-summit
  Body: { lead_ids: [...] }  -- empty = sync all pending
```

### The Summit.AI Integration
```
GET    /api/summit/config
PUT    /api/summit/config
POST   /api/summit/test
GET    /api/summit/sync-status
```

---

## Accela API Integration

### Authentication (On-Demand Token Refresh)
- Check `token_expires_at` before each API call
- If expired, call OAuth to get new token
- Update `accela_access_token` and `token_expires_at`
- **CRITICAL:** Use header `Authorization: {token}` (NO "Bearer " prefix!)

### Permit Pulling Process
```python
# 1. Get permits
GET /v4/records?module=Building&openedDateFrom=2010-01-01&openedDateTo=2015-12-31&limit=100

# 2. Filter for HVAC (client-side)
hvac_permits = [p for p in result if 'Mechanical' in p['type']['value']]

# 3. Enrich each permit
for permit in hvac_permits:
    addresses = GET /v4/records/{id}/addresses
    owners = GET /v4/records/{id}/owners
    parcels = GET /v4/records/{id}/parcels  # year_built, sqft, value

    store_permit(permit, addresses, owners, parcels)
```

---

## The Summit.AI Integration

### Sync Mode: Manual Batch Selection
User workflow:
1. Review leads in dashboard
2. Select specific leads (checkboxes)
3. Click "Send to The Summit.AI"
4. Backend creates/updates contacts
5. Dashboard shows sync status

### Data Mapping
```python
{
  "firstName": owner_name.split()[0],
  "lastName": owner_name.split()[-1],
  "email": owner_email,
  "phone": owner_phone,
  "address1": property_address,

  "customField": {
    "permit_id": accela_record_id,
    "permit_date": opened_date,
    "year_built": year_built,
    "square_footage": square_footage,
    "property_value": property_value,
    "county": county_name
  },

  "tags": ["hvac-lead", f"permit-{year}", county_name]
}
```

### Duplicate Handling
- Search Summit.AI by phone/email first
- If exists: Update contact, add tags
- If new: Create contact
- Store `summit_contact_id` in leads table

---

## Frontend Dashboard

### 1. Counties View
- Card-based layout
- Status: 🟢 Connected | ⚠️ Token Expired | 🔴 Error
- Last pull timestamp
- "Pull Leads" button per county
- "Run All Counties" bulk action

### 2. Pull Permits Modal
- Date range (from/to)
- OR "Permits older than X years"
- Max results dropdown
- "Finaled only" checkbox
- Test connection before pull

### 3. Leads Dashboard
- Table/card view with filters (county, sync status)
- Checkbox selection
- Visual sync indicators:
  - 🟡 Pending
  - ✅ Synced (with timestamp)
  - 🔴 Failed (with error)
- Bulk action: "Send Selected to The Summit.AI"

### 4. Settings Page
- The Summit.AI API configuration
- API key input (masked)
- Location ID
- Test connection button

### 5. County Configuration (Add/Edit Modal)
**Step 1:** County name
**Step 2:** Accela credentials (app_id, app_secret, environment)
**Step 3:** Test connection → Save

---

## Security

- All credentials encrypted at rest (Supabase)
- HTTPS only (TLS 1.3)
- CORS restricted to frontend domain
- API keys masked in UI (`••••••••`)
- Test credentials before saving
- Input validation (Pydantic)

---

## Deployment

**Frontend:** Vercel (auto-deploy from GitHub)
**Backend:** Railway (auto-deploy from GitHub) - https://hvac-backend-production-11e6.up.railway.app
**Database:** Supabase (cloud-hosted PostgreSQL)

**Environment Variables:**
- Backend: `SUPABASE_URL`, `SUPABASE_KEY`, `SUMMIT_API_KEY`
- Frontend: `VITE_API_URL`

---

## Development Phases

**Phase 1:** Foundation
- Project structure (frontend + backend repos)
- Supabase setup and migrations
- Accela API integration + token refresh
- County CRUD operations

**Phase 2:** Permit Pulling
- Implement permit pulling from Accela
- Property enrichment (parcels, owners, addresses)
- Store full data in database
- Basic county management UI

**Phase 3:** Lead Management
- Convert permits to leads
- Leads dashboard with filters
- The Summit.AI sync logic
- Sync status tracking

**Phase 4:** Polish & Deploy
- UI/UX refinements
- Error handling
- Deploy to production
- Testing with real data

---

## Success Criteria

- Pull HVAC permits from 2+ counties
- Property enrichment working (age, sqft, value)
- Manual sync to Summit.AI with 95%+ success
- Clear sync status in dashboard
- Add new counties without code changes
- Token auto-refresh seamless

---

## Notes

- Schema may need adjustment after first real API call
- All permit data stored in `raw_data` JSONB (nothing lost)
- Automated outreach handled in The Summit.AI workflows
- Future: Multi-tenant SaaS with GHL OAuth
