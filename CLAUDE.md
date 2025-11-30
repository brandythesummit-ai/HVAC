# HVAC Lead Generation Platform - Project Memory

## Project Overview

This is a full-stack HVAC lead generation platform that pulls permit data from county Accela systems, enriches it with property information, and syncs qualified leads to Summit.AI CRM.

**Core Workflow:** Pull HVAC permits → Enrich with property data → Convert to leads → Sync to CRM

## Tech Stack

### Frontend
- **Framework:** React 19.2.0 with React Router 7.9.6
- **Build Tool:** Vite 7.2.4
- **State Management:** TanStack React Query 5.90.11
- **HTTP Client:** Axios 1.13.2
- **Styling:** TailwindCSS 4.1.17 with PostCSS
- **Icons:** Lucide React
- **Language:** JavaScript ES modules
- **Deployment:** Vercel
- **Production URL:** https://hvac-liard.vercel.app/leads

### Backend
- **Framework:** FastAPI 0.104.0+
- **ASGI Server:** Uvicorn 0.24.0+
- **Database:** Supabase (PostgreSQL with Python client)
- **Data Validation:** Pydantic 2.5.0
- **HTTP Client:** httpx (async)
- **Security:** Fernet encryption for credentials
- **Language:** Python 3.11
- **Deployment:** Railway/Render

### External APIs
- **Accela Civic Platform V4 API** (OAuth refresh_token flow, 15-min expiration)
- **Summit.AI CRM API** (Private integration with static token)

## Architecture Patterns

### Backend Structure
```
/backend/app
├── main.py              # FastAPI app initialization
├── config.py            # Pydantic settings from environment
├── database.py          # Supabase connection
├── /models              # Pydantic request/response models
├── /routers             # API endpoint definitions
└── /services            # Business logic (Accela, Summit clients)
```

**Pattern:** Routers → Models → Services (layered architecture)

### Frontend Structure
```
/frontend/src
├── /api                 # API client layer (Axios)
├── /components          # Reusable React components
├── /pages               # Top-level page components
├── /hooks               # Custom React Query hooks
└── /utils               # Formatters and utilities
```

**Pattern:** Functional components with hooks, React Query for server state

### Database Schema
Key tables:
- **agencies** - Contractor organizations (multi-tenant)
- **counties** - Accela API configurations per agency
- **permits** - HVAC permits (JSONB raw_data for full API response)
- **leads** - Converted permits (tracks CRM sync status)
- **sync_config** - Agency sync configuration

## Code Style Conventions

### Python (Backend)
- Use **snake_case** for functions/variables, **PascalCase** for classes
- Always use **async/await** for I/O operations
- Add type hints for all Pydantic models
- Use docstrings for complex functions: `"""Description."""`
- Error handling: Raise `HTTPException` for API errors
- Return standardized responses: `{"success": bool, "data": any, "error": str|null}`

### JavaScript/React (Frontend)
- Use **camelCase** for variables/functions, **PascalCase** for components
- Functional components with hooks only (no class components)
- Custom hooks for API calls (useCounties, usePermits, useLeads)
- TailwindCSS utility classes (no inline styles)
- Import ES modules: `import { useState } from 'react'`
- Constants defined at module level

### Git Conventions
- **Main branch:** `main` (production)
- **Commit style:** Conventional commits (feat:, fix:, enhance:, etc.)
- Descriptive commit messages explaining the "why"

## Testing Requirements (CRITICAL)

### E2E Testing with Playwright
- **ALWAYS test with Playwright when making changes to features**
- **Test timeout: Maximum 15 seconds** - never longer
- **Test URL: https://hvac-liard.vercel.app/counties**
- Run tests after making changes and **fix any errors found before completing**
- Sequential execution (workers: 1) to avoid data races
- Screenshots/videos on failure only

### Test Commands
```bash
npm run test                           # Run all E2E tests
npm run test:ui                        # Interactive test runner
npm run test:headed                    # Browser visible
npm run test:debug                     # Debug mode
npm run test:pull-permits              # Specific test
npm run test:report                    # View HTML results
```

### Testing Philosophy
- E2E testing is MANDATORY when applicable
- Always verify changes work in production environment
- Fix issues immediately when tests fail

## Common Commands

### Frontend Development
```bash
cd frontend
npm run dev              # Vite dev server (port 3000, proxies /api → localhost:8000)
npm run build            # Production build to /dist
npm run preview          # Preview production build
npm run lint             # ESLint check
```

### Backend Development
```bash
cd backend
source venv/bin/activate  # Activate virtual environment
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload          # Dev with auto-reload
python -m app.main                     # Direct execution

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Database
```bash
# Generate encryption key for credentials
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## API Patterns

### Standard Response Format
All endpoints return:
```json
{
  "success": true/false,
  "data": { /* payload */ },
  "error": null /* or error message */
}
```

### Key Endpoints
```
POST   /api/counties                        - Create county config
GET    /api/counties                        - List all
POST   /api/counties/{id}/test              - Test Accela connection
POST   /api/counties/{id}/oauth/*           - OAuth flow
POST   /api/counties/{id}/pull-permits      - Pull HVAC permits

GET    /api/leads                           - List leads
POST   /api/leads/create-from-permits       - Convert permits to leads
POST   /api/leads/sync-to-summit            - Sync to CRM
PUT    /api/leads/{id}/notes                - Update notes

GET    /api/summit/config                   - Get CRM config
PUT    /api/summit/config                   - Update config
```

### Important API Details
- **CORS:** Configured for `localhost:3000`, `localhost:5173`, and `*.vercel.app`
- **OAuth:** Accela tokens auto-refresh before each API call (15-min expiration)
- **Encryption:** All credentials encrypted with Fernet in DB, decrypted on-demand

## Accela API Documentation & Resources

### Official API Documentation
- [V4 API Index](https://developer.accela.com/docs/construct-apiIndex.html) - Complete endpoint catalog
- [Records API Reference](https://developer.accela.com/docs/api_reference/api-records.html#operation/v4.get.records) - GET /v4/records specification ⭐
- [Using the Accela API](https://developer.accela.com/docs/construct-usingConstructApi.html) - REST guidelines
- [Your First API Call](https://developer.accela.com/docs/construct-firstApiCall.html) - Getting started
- [V4 API Release Notes](https://developer.accela.com/docs/construct_api_v4_rel_notes.html) - Version history

### Key Endpoints Currently Used

**Records (Permits):**
- `GET /v4/records` - Search permits (module=Building, date filters) ✅
- `GET /v4/records/{id}/addresses` - Get permit addresses ✅
- `GET /v4/records/{id}/owners` - Get property owners ✅
- `GET /v4/records/{id}/parcels` - Get parcel data ✅

**Available for Future Enhancement:**
- `GET /v4/records/{id}/comments` - Permit comments/notes
- `GET /v4/records/{id}/inspections` - Inspection records
- `GET /v4/records/{id}/contacts` - Associated contacts
- `GET /v4/records/{id}/professionals` - Licensed professionals
- `GET /v4/records/{id}/conditions` - Permit conditions
- `GET /v4/records/{id}/documents` - Attached documents
- `GET /v4/records/{id}/fees` - Fee schedule
- `POST /v4/search/records` - Advanced search

### Data Completeness Requirement ⚠️ CRITICAL

**ALL data retrieved from Accela SHALL be visible in the Leads tab for every permit pulled.**

**Current Status:**
- ✅ We fetch: permit + addresses + owners + parcels
- ✅ We store: ALL raw responses in `permits.raw_data` (JSONB)
- ❌ We display: Only ~10 extracted fields in Leads table
- ❌ **PROBLEM:** `raw_data` contains 50+ fields that are hidden from users

**What needs to be displayed:**
All fields from `permits.raw_data.permit` including:
- Basic: type, description, status, customId, module
- Dates: openedDate, closedDate, statusDate, completedDate
- Values: jobValue, estimatedCost, estimatedTotalFees, balance
- IDs: id, trackingId, customId, referenceNumber
- Location: Full addresses array (not just first one)
- Ownership: Full owners array with all contact methods
- Parcels: Complete parcel data with all valuations
- Agency-specific: Custom fields unique to each county
- **Everything else in the raw JSON response**

### Query Parameters for GET /v4/records

Parameters we currently use:
- `module` = "Building" (required for our use case)
- `openedDateFrom` / `openedDateTo` - Date range
- `limit` - Max results (default 100, max 9999)
- `status` - Optional (e.g., 'Finaled', 'Issued')
- `type` - Optional (e.g., 'Mechanical') - we filter client-side instead

**Available but not used:**
- `offset` - Pagination
- `customId` - Specific permit number
- `recordClass` - Record classification
- `balanceStart` / `balanceEnd` - Fee balance filters
- See full list: [Records API Reference](https://developer.accela.com/docs/api_reference/api-records.html#operation/v4.get.records)

### Field Availability by Agency

**IMPORTANT:** Not all agencies configure the same fields in Accela.

Always check `raw_data` to see what YOUR specific county returns. Common variations:
- Some counties include `jobValue`, others don't
- Custom fields vary widely (e.g., "contractor_license", "special_notes")
- Inspection workflows differ by jurisdiction
- Fee structures are agency-specific

This is why we store the complete `raw_data` - to capture everything regardless of schema differences.

### GitHub Resources

[Accela-Inc GitHub](https://github.com/Accela-Inc) contains infrastructure tools, NOT API SDKs or documentation. Use the official REST API docs above instead.

## Security Practices

- **Never commit .env files** (use .env.example for templates)
- **All API keys in environment variables** (Supabase, Summit.AI, encryption key)
- **Encrypt sensitive credentials** using Fernet before storing in DB
- **OAuth tokens auto-rotate** transparently
- See `/SECURITY_TODO.md` for outstanding security tasks

## Data Flow & Enrichment Strategy

1. **Pull Permits:** User selects county + date range → Accela API pulls permits with **API-level type filtering** ("Residential Mechanical Trade Permit") → **Automatic pagination** fetches all results in chunks of 100 → Enrich with addresses/owners/parcels → Store in DB with full JSONB raw_data
2. **Create Leads:** User selects permits from table → Convert to leads → Store with sync status
3. **Sync to CRM:** User selects leads → POST to Summit.AI API → Update sync_status
4. **Frontend State:** React Query caches API responses, auto-refetches on mutations

### Permit Filtering & Pagination (Updated 2025-11-29)

**API-Level Filtering:**
- Uses Accela's `type` parameter to filter at API level (more efficient than client-side)
- Current filter: `"Residential Mechanical Trade Permit"` (exact type from HCFL Accela portal)
- Reduces data transfer (only HVAC permits returned, not all Building permits)
- Configured in `backend/app/routers/permits.py` lines 176-189

**Automatic Pagination:**
- Fetches permits in chunks of 100 (Accela API max per request)
- Uses `offset` parameter to paginate through results
- Continues until reaching requested limit or no more results available
- Implemented in `backend/app/services/accela_client.py` lines 323-418
- Fetching 1000 permits = ~10 API calls = 10-15 seconds (within 120s timeout)

**Key Benefits:**
- ✅ Can fetch 1000+ permits (not limited to first 100)
- ✅ More efficient (API does filtering, not client-side)
- ✅ Exact type matching (uses county's actual permit type name)
- ✅ Complete logging for diagnostics (pages fetched, total returned)

## Supabase MCP Configuration

### Project Identification ⚠️ CRITICAL

**Always use the correct Supabase project ID from environment variables:**
- Project ID: `jlammryvteuhrlygpqif` (stored in `$SUPABASE_PROJECT_REF`)
- Project Name: `hvac-lead-gen`
- Dashboard: https://supabase.com/dashboard/project/jlammryvteuhrlygpqif

**IMPORTANT:**
Never hardcode project IDs. Always use the `$SUPABASE_PROJECT_REF` environment variable when calling Supabase MCP tools. Using the wrong project ID will result in permission errors even though you have full access.

### MCP Tool Capabilities

The Supabase MCP provides write access:
- `mcp__supabase__execute_sql` - Full DDL/DML permissions (CREATE, ALTER, INSERT, UPDATE, DELETE)
- `mcp__supabase__apply_migration` - Apply named migrations with SQL
- `mcp__supabase__list_tables` - View schema structure
- `mcp__supabase__list_migrations` - Track applied migrations

### PostgREST Schema Cache

**What is it:**
PostgREST (Supabase's REST API layer) caches the database schema for performance. When you add columns via direct SQL migrations, PostgREST doesn't automatically know about them.

**When to reload:**
After applying migrations that:
- Add new columns to existing tables
- Create new tables that will be accessed via REST API
- Modify table constraints or indexes used by the API

**How to reload manually:**
1. Go to: https://supabase.com/dashboard/project/jlammryvteuhrlygpqif/settings/api
2. Click: "Reload schema" button under PostgREST Settings
3. Wait ~5 seconds for confirmation

**Symptoms of stale cache:**
- `PGRST204` errors (column not found in schema cache)
- Inserts/updates failing on new columns despite migrations being applied
- REST API returning 400 errors for valid column names

**Note:** Schema cache usually auto-reloads within minutes, but manual reload ensures immediate availability.

## Project Documentation

Key reference files:
- `/backend/README.md` - Backend architecture and API docs
- `/frontend/README.md` - Frontend setup and tech stack
- `/database/README.md` - Schema, migrations, setup
- `/DEPLOYMENT_GUIDE.md` - Production deployment
- `/docs/plans/2025-11-28-hvac-lead-gen-design.md` - Full system design

FastAPI auto-generates API docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000  # Backend API URL
```

### Frontend (.env.production) ⚠️ CRITICAL
```
VITE_API_URL=https://hvac-backend-production-11e6.up.railway.app
```
**IMPORTANT:** Vercel deployments use `.env.production` to configure the backend API URL. Without this file, the frontend will default to `localhost:8000` and API calls will fail in production.

**Current Production Configuration:**
- Backend: Railway at `https://hvac-backend-production-11e6.up.railway.app`
- Frontend: Vercel at `https://hvac-liard.vercel.app`

### Backend (.env)
```
SUPABASE_URL=...
SUPABASE_KEY=...
SUMMIT_API_KEY=...
ENCRYPTION_KEY=...  # Fernet key for credential encryption
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://*.vercel.app
```

## When to Update CLAUDE.md

⚠️ **IMPORTANT:** ALWAYS ask the user for approval before committing changes to CLAUDE.md

**Claude should recommend updating this file when:**
- Adding new dependencies or changing tech stack
- Establishing new coding conventions or patterns
- Adding new API endpoints or changing response formats
- Updating deployment configuration
- Introducing new workflows or common commands
- Making architectural decisions that affect future development
- Adding new testing requirements or changing test strategies
- Discovering new issues or constraints that affect development

## Important Notes

- **Client-side filtering:** HVAC permits filtered by "Mechanical" type in backend due to Accela API limitations
- **JSONB storage:** Full Accela API response stored in permits.raw_data for complete data preservation
- **Multi-tenant:** System supports multiple agencies via agencies table
- **Test target:** E2E tests run against production Vercel deployment at https://hvac-liard.vercel.app/counties
