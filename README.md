# HVAC Lead Generation Platform

**Automated permit data collection and CRM integration for HVAC contractors**

Transform county building permits into qualified replacement leads with intelligent property-centric scoring and seamless Summit.AI CRM integration.

---

## 🎯 What This Does

This platform automatically pulls HVAC permit data from county Accela systems, enriches it with property information, scores leads based on HVAC system age, and syncs qualified opportunities to your Summit.AI CRM.

**Core Workflow:**
```
County Permits → Property Enrichment → Lead Scoring → CRM Sync
```

## 🏁 MVP Requirements

### Florida Statewide Coverage
**Scope:** All **67 Florida counties** must be pre-configured for MVP launch.

**County Configuration Per County:**
- County name, state abbreviation
- Permit portal URL (official county permit search page)
- Platform identification (Accela, EnerGov, eTRAKiT, Tyler, OpenGov, Custom, Unknown)
- Access method (Public API, UI-only, Open Data Portal, Custom Integration)
- Connection status (Connected, Pending, Not Configured)

**Current Status (V1):**
- ✅ **Accela Integration:** Production-ready (validated with Hillsborough County)
- 🚧 **Multi-Platform Support:** Planned for V2 (see Future Vision below)
- 📊 **Current Coverage:** ~25-30 Florida counties use Accela (immediately accessible)
- 🎯 **Remaining Counties:** 37-42 counties require V2 multi-platform integrations

**Why All 67 Counties?**
Florida's climate and aging HVAC systems create high replacement demand. Statewide coverage ensures HVAC contractors can target any Florida market without artificial geographic limitations.

**Implementation Note:** V1 focuses on Accela-based counties. V2 adds hybrid automated platform detection for complete coverage (see Future Vision section).

## ✨ Key Features

### 🏢 Multi-County Permit Pulling
- Connect to any county using Accela Civic Platform V4 API
- **Adaptive rate limiting** - header-based throttling prevents API account suspension
- Pull 25 years of historical HVAC permits for comprehensive lead database
- Automated daily incremental pulls to catch new installations
- Automatic pagination (handles 1,000+ permits per pull)
- API-level filtering for HVAC permits only (more efficient)

**Pull Strategy:**
- **Initial Pull:** 25 years historical, oldest→newest (2000→2025)
- **Post-Initial:** Every 7 days, pull last 8 days (1-day overlap prevents gaps)
- **Lead Qualification:** Only HVAC systems 5+ years old qualify for CRM sync

### 🏠 Property-Centric Data Model
- **Address Normalization** - Matches multiple permits to same property
- **HVAC Age Tracking** - Calculates system age from most recent permit
- **Intelligent Lead Scoring** (0-100) based on replacement urgency
- **Automatic Tiering**:
  - 🔥 **HOT (80-100):** 15-20+ years old - Replacement imminent
  - 🌡️ **WARM (60-75):** 10-15 years old - Maintenance + potential replacement
  - 🧊 **COOL (40-55):** 5-10 years old - Maintenance focus
  - ❄️ **COLD (0-35):** <5 years old - **Not qualified for CRM sync** (too new for replacement outreach)

**Lead Qualification Rule:** Only properties with HVAC systems **5+ years old** are created as leads and synced to CRM. Properties with <5 year old systems are tracked in the database but NOT converted to leads or synced.

**Rationale:** HVAC systems typically last 10-20 years. Systems <5 years old are extremely unlikely to need replacement, making them low-value leads that waste sales effort and damage contractor reputation.

### Property Aggregation Example

**Scenario:** 123 Main St has two HVAC permits:
- **2005:** Original installation (permit #1)
- **2025:** Replacement (permit #2)

**System Behavior:**
1. Both permits stored in database (complete history tracked)
2. Property record uses **MOST RECENT date** (2025)
3. HVAC age calculated: **0 years old**
4. Lead score: **21 points** (COLD tier)
5. Lead status: **NOT QUALIFIED** (< 5 years)
6. CRM sync: **BLOCKED** (will not sync to Summit.AI)

**Key Insight:** Newer permits override older ones for age calculation. A 2025 replacement makes the property "new" again, disqualifying it as a lead until 2030+.

This intelligent aggregation ensures contractors target properties genuinely needing replacement, not recent installations that would waste sales effort.

### 🤖 Background Job Processing
- **25-Year Historical Pulls** - Process decades of permits automatically
- **PostgreSQL-Based** - No Redis, Celery, or external dependencies
- **Real-Time Progress Tracking** - Monitor permits/second, ETA, stats
- **Automatic Retries** - Handles transient API failures
- **Graceful Cancellation** - Stop long-running jobs without data loss

### 📅 Automated Scheduling
- **Initial Historical Pull** - Automatically pulls 25 years of historical permits when county is added (oldest→newest: 2000→2025)
- **Incremental Pulls Every 7 Days** - After initial pull completes, automatically fetches last 8 days of permits every 7 days
- **Overlap for Gap Prevention** - 8-day window with 7-day frequency ensures no permits missed (1-day overlap)
- **Hourly Background Checks** - Scheduler monitors for due counties every hour
- **Configurable Per County** - Enable/disable automation individually per county

### 🔄 Summit.AI CRM Integration
- **Batch Lead Sync** - Push qualified leads to Summit.AI (white-label HighLevel)
- **Contact Deduplication** - Searches by phone/email before creating
- **Automatic Tagging** - Labels leads with "hvac-lead" tag
- **Sync Status Tracking** - Monitors pending/synced/failed states

### 🛡️ Security & Reliability
- **Encrypted Credentials** - Fernet encryption for Accela secrets and API keys
- **Automatic Token Refresh** - Handles Accela's 15-minute OAuth expiration
- **Adaptive Rate Limiting** - Dynamic throttling prevents 429 errors and API suspension
- **Comprehensive Health Monitoring** - 8 components with priority-based checking
- **CORS Protection** - Restricted to configured frontend origins

## 🚀 Live Deployment

- **Frontend:** https://hvac-liard.vercel.app
- **Backend API:** https://hvac-backend-production-11e6.up.railway.app
- **Database:** Supabase (PostgreSQL)
- **Status:** ✅ Fully operational

## 🛠️ Tech Stack

### Frontend
- React 19.2.0 with React Router 7.9.6
- Vite 7.2.4 (build tool)
- TanStack React Query 5.90.11 (server state)
- TailwindCSS 4.1.17 (styling)
- Deployed on Vercel

### Backend
- FastAPI 0.104.0+ (Python web framework)
- Uvicorn 0.24.0+ (ASGI server)
- Supabase (PostgreSQL database)
- Httpx (async HTTP client)
- Deployed on Railway

### External APIs
- **Accela Civic Platform V4** - County permit data
- **Summit.AI (HighLevel)** - CRM integration

## 📁 Project Structure

```
HVAC/
├── frontend/          # React + Vite frontend
│   ├── src/
│   │   ├── api/       # API client layer
│   │   ├── components/  # React components
│   │   ├── pages/     # Page components
│   │   └── hooks/     # Custom React Query hooks
│   └── README.md
│
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── main.py    # FastAPI app entry
│   │   ├── config.py  # Environment settings
│   │   ├── models/    # Pydantic models
│   │   ├── routers/   # API endpoints
│   │   ├── services/  # Business logic (Accela, Summit clients)
│   │   └── workers/   # Background job processor
│   ├── README.md
│   └── .env.example
│
├── database/          # PostgreSQL schema & migrations
│   ├── migrations/    # SQL migration files
│   ├── README.md
│   └── seed.sql
│
└── docs/
    └── plans/         # Design documents
```

**Current Structure:** V1 (Accela-only integration)

**V2 Additions (Future):**
```
backend/app/services/
  ├── discovery_service.py      # County permit portal discovery
  ├── fingerprinting_service.py # Platform identification
  └── integrations/             # Per-platform adapters
        ├── accela_adapter.py   # ✅ Complete
        ├── energov_adapter.py  # 🚧 Planned
        ├── etrakit_adapter.py  # 🚧 Planned
        └── tyler_adapter.py    # 🚧 Planned

database/migrations/
  └── 016_create_platform_detections.sql
```

## 🚦 Quick Start

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.11+ (for backend)
- Supabase account (free tier works)
- Accela API credentials from your county
- Summit.AI API key (optional for CRM sync)

### 1. Clone Repository
```bash
git clone https://github.com/brandythesummit-ai/HVAC.git
cd HVAC
```

### 2. Set Up Database
Follow the [database README](database/README.md) to:
- Create Supabase project
- Run migrations (9 tables)
- Optionally seed test data

### 3. Configure Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your Supabase URL, keys, and encryption key
```

Generate encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. Configure Frontend
```bash
cd frontend
npm install

# For local development
echo "VITE_API_URL=http://localhost:8000" > .env

# For production (Vercel)
echo "VITE_API_URL=https://hvac-backend-production-11e6.up.railway.app" > .env.production
```

### 5. Run Development Servers

**Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
# Runs on http://localhost:8000
# API docs: http://localhost:8000/docs
```

**Frontend:**
```bash
cd frontend
npm run dev
# Runs on http://localhost:3000
```

## 📖 Documentation

- **[Frontend README](frontend/README.md)** - React app setup, tech stack, component architecture
- **[Backend README](backend/README.md)** - API endpoints, background jobs, deployment
- **[Database README](database/README.md)** - Schema, migrations, setup instructions
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Production deployment to Railway + Vercel
- **[Design Document](docs/plans/2025-11-28-hvac-lead-gen-design.md)** - Complete system design
- **[CLAUDE.md](CLAUDE.md)** - Project memory for AI-assisted development

## 🔑 Key Concepts

### Property-Centric vs Permit-Centric
Traditional systems track individual permits. This platform groups all permits by property address, enabling:
- Accurate HVAC age calculation (most recent installation)
- Lead qualification based on replacement urgency
- Complete permit history per property
- Intelligent scoring based on multiple factors

### Lead Scoring Algorithm
Each property receives a 0-100 score based on:
- **HVAC Age** (70% weight) - Older systems = higher urgency
- **Property Value** (15% weight) - Higher value = better customer
- **Permit History** (15% weight) - Multiple permits = active maintenance

### Background Job System
Uses PostgreSQL-based polling (no external queue needed):
- **Job Processor** polls `background_jobs` table every 5 seconds
- **Pull Scheduler** checks for due counties every hour
- Both run as FastAPI background tasks (start automatically)

## 🌐 API Endpoints

### Health & Status
- `GET /health` - Comprehensive system health (8 components)

### County Management
- `POST /api/counties` - Add county with Accela credentials
- `GET /api/counties` - List all counties
- `POST /api/counties/{id}/test` - Test Accela connection
- `GET /api/counties/{id}/rate-limit-stats` - Get Accela API rate limit stats
- `DELETE /api/counties/{id}` - Remove county

### Permit Operations
- `POST /api/counties/{id}/pull-permits` - Pull permits (with filters)
- `GET /api/permits` - List permits with filters

### Lead Management
- `GET /api/leads` - List leads with filters
- `POST /api/leads/create-from-permits` - Convert permits to leads
- `POST /api/leads/sync-to-summit` - Sync to Summit.AI CRM

### Background Jobs
- `POST /api/background-jobs/counties/{id}/jobs` - Create async job
- `GET /api/background-jobs/jobs/{id}` - Get job status with progress
- `POST /api/background-jobs/jobs/{id}/cancel` - Cancel running job

Full API documentation: http://localhost:8000/docs (Swagger UI)

## 🔐 Security

- **Credential Encryption** - All API keys/secrets encrypted with Fernet
- **OAuth Auto-Refresh** - Transparent token renewal (Accela 15-min expiration)
- **CORS Protection** - Restricted to configured frontend origins
- **Input Validation** - Pydantic models enforce type safety
- **Connection Testing** - Verify credentials before saving

## 📊 Database Schema

9 tables organized in multi-tenant architecture:

```
agencies (HVAC contractor organizations)
  └── counties (Accela API configurations)
        ├── permits (raw permit data with JSONB storage)
        │     ├── leads (CRM-ready leads)
        │     └── properties (property-centric aggregation)
        ├── pull_history (audit trail)
        └── county_pull_schedules (automation config)
  ├── sync_config (CRM sync settings)
  └── background_jobs (async job tracking)
```

See [database/README.md](database/README.md) for complete schema documentation.

## 🧪 Testing

### E2E Testing with Playwright
```bash
cd frontend
npm run test              # Run all E2E tests
npm run test:ui           # Interactive test runner
npm run test:headed       # Browser visible
npm run test:report       # View HTML report
```

**Test Target:** Production deployment at https://hvac-liard.vercel.app

## 🚀 Deployment

### Production Stack
- **Frontend:** Vercel (automatic deployments from main branch)
- **Backend:** Railway (automatic deployments from main branch)
- **Database:** Supabase (managed PostgreSQL)

### Environment Variables

**Backend (Railway):**
```bash
SUPABASE_URL=https://jlammryvteuhrlygpqif.supabase.co
SUPABASE_KEY=<your-anon-key>
ENCRYPTION_KEY=<fernet-key>
SUMMIT_API_KEY=<your-summit-key>
SUMMIT_LOCATION_ID=<your-location-id>
CORS_ORIGINS=https://hvac-liard.vercel.app,https://hvac-*.vercel.app
ENVIRONMENT=production
```

**Frontend (Vercel):**
```bash
VITE_API_URL=https://hvac-backend-production-11e6.up.railway.app
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete deployment instructions.

## 🐛 Troubleshooting

### Backend won't start
- Verify `.env` has all required variables (use `.env.example` as template)
- Check encryption key is valid Fernet key
- Ensure Supabase URL and key are correct

### Accela API errors
- Verify credentials match county's Accela environment (PROD, TEST, etc.)
- Check that OAuth scope includes all required endpoints
- Authorization header does NOT use "Bearer " prefix (Accela-specific)

### Frontend shows "Network Error"
- Verify `VITE_API_URL` is set correctly in `.env` (local) or `.env.production` (Vercel)
- Check CORS_ORIGINS in backend includes your frontend domain
- Test backend health: `curl https://hvac-backend-production-11e6.up.railway.app/health`

### Database errors
- Ensure all 9 tables created (run migrations in order)
- Check Supabase connection string is correct
- Verify RLS policies aren't blocking queries (disable for testing)

---

## 🔮 Future Vision: V2 Multi-Platform County Detection

> **Status:** NOT IMPLEMENTED - This section documents the planned V2 architecture for multi-platform permit system support.
>
> **Decision Point:** Implement V2 when V1 Accela counties generate consistent ROI and contractors request expanded coverage.

### Why Multi-Platform Support?

**The Problem:** Florida's 67 counties use diverse permit platforms:
- **Accela:** 40-45% of counties (~25-30 counties) - ✅ V1 Complete
- **EnerGov:** 15-22% of counties (~10-15 counties) - 🚧 V2 Required
- **Custom Systems:** 22-30% of counties (~15-20 counties) - 🚧 V2 Required
- **Tyler/eTRAKiT/OpenGov:** 8-23% combined (~5-15 counties) - 🚧 V2 Required

**Current Limitation:** V1 only supports Accela, leaving 37-42 counties inaccessible.

**V2 Goal:** Hybrid automated detection + manual review achieves 100% Florida coverage.

---

### The Hybrid Automated Detection System

**Core Principle:** Automate 70-90% of platform detection, human review handles edge cases (custom portals, redirects, third-party add-ons).

**4-Phase Detection Pipeline:**

#### Phase 1: Discovery - Find Permit Portal URLs

**Input:**
- List of 67 Florida counties
- Each county's official website root domain (e.g., hillsboroughcounty.org)

**Process:**
1. Web crawler navigates county site structure
2. Searches for keywords: "Permits", "Building", "Development Services", "Citizen Access", "Inspections"
3. Follows outbound links and resolves redirect chains
4. Captures final destination URL

**Output:**
- Canonical permit portal URL per county
- Source page that linked to it
- Redirect chain (if applicable)

**Example - Hillsborough County:**
```
Root: hillsboroughcounty.org
Path: /residents/building-development
Link: "Search Building Permits"
Redirect: hillsboroughcounty.org → aca-prod.accela.com
Final URL: https://aca-prod.accela.com/HCFL/Default.aspx
```

#### Phase 2: Fingerprinting - Identify Platform

**Input:** Permit portal URL from Phase 1

**Process:**
Like Wappalyzer but tuned for government permitting stacks. Checks for:

**Platform Signatures:**

| Platform | Detection Signals |
|----------|------------------|
| **Accela Citizen Access** | • URL pattern: `aca-prod.accela.com/<agency>/` or `aca.accela.com`<br>• HTML strings: "Accela Citizen Access", "Accela Inc"<br>• JS bundles: `accela-*.js`<br>• Login endpoint: `/Account/Login.aspx`<br>• Cookies: `ASP.NET_SessionId`, `.ACAASPXAUTH` |
| **EnerGov** | • URL pattern: `energov*.tylertech.com`<br>• HTML: "Tyler Technologies", "EnerGov"<br>• JS: `energov-app.js`<br>• API: `/api/EnerGov/` |
| **eTRAKiT** | • URL: `etrakit.com` subdomain<br>• HTML: "e-TRAKiT", "Superion"<br>• Login: `/eTRAKiT/Login.aspx` |
| **Tyler Tech (other)** | • URL: `tylertech.com` or `tylertechnologies.com`<br>• HTML: "Tyler Technologies"<br>• Multiple product lines |
| **OpenGov** | • URL: `opengov.com` subdomain<br>• HTML: "OpenGov Inc"<br>• API: `/api/opengov/` |
| **Custom/Legacy** | • No vendor signatures<br>• County-specific branding only<br>• Legacy ASP/PHP patterns |

**Output:**
```json
{
  "county": "Hillsborough",
  "platform": "Accela Citizen Access",
  "confidence": 0.95,
  "evidence": [
    "URL: aca-prod.accela.com/HCFL/",
    "HTML: 'Accela Citizen Access' found 3x",
    "Cookie: .ACAASPXAUTH present"
  ],
  "vendor": "Accela Inc"
}
```

**Confidence Scoring:**
- **0.9-1.0:** High (multiple strong signals) → Auto-approve
- **0.6-0.89:** Medium (some signals) → Human review
- **0.0-0.59:** Low (conflicting/weak signals) → Human review

#### Phase 3: Access Classification

**Input:** Platform identification from Phase 2

**Process:** For each detected platform, determine realistic data access path:

**Access Types:**

| Access Type | Description | Example |
|-------------|-------------|---------|
| **Public API** | REST/SOAP API available (may require approval/keys) | Accela V4 API, EnerGov API |
| **UI-Only** | No API - only web search interface | Custom county portals |
| **Open Data Portal** | County publishes permits to Socrata/ArcGIS | Some progressive counties |
| **Custom Integration** | Requires per-county engineering | Legacy systems, locked-down agencies |

**For Accela Specifically:**
- Presence of Citizen Access ≠ guaranteed API access
- API requires:
  1. Agency approval (contact county IT)
  2. OAuth app registration
  3. Scope permissions (records, addresses, parcels)
- **Signal Strength:** High (Accela APIs well-documented, consistent across agencies)

**Output:**
```json
{
  "county": "Hillsborough",
  "platform": "Accela Citizen Access",
  "access_classification": "Public API (requires approval)",
  "integration_effort": "Low (V1 adapter exists)",
  "notes": "Use existing AccelaClient with county-specific OAuth app"
}
```

#### Phase 4: Human-in-the-Loop Review

**When Triggered:**
- Confidence score < 0.9
- Platform = "Custom" or "Unknown"
- Conflicting signals detected
- Redirect chain >3 hops
- Multiple vendor signatures found

**Review Interface (ASCII Mockup):**
```
╔════════════════════════════════════════════════════════════════╗
║ Platform Detection Review - Queue: 12 counties                 ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║ County: Sarasota County, Florida                              ║
║ Portal URL: https://sarasota.county-permits.com               ║
║                                                                ║
║ Detected Platform: Unknown (Confidence: 0.45)                 ║
║                                                                ║
║ Evidence:                                                      ║
║   • HTML: "Permit Management System" (generic)                ║
║   • No vendor signatures found                                ║
║   • Custom login: /pms/login.php                              ║
║   • Uses PHP (not common vendor pattern)                      ║
║                                                                ║
║ Screenshot: [View Portal]  HTML: [View Source]                ║
║                                                                ║
║ ┌──────────────────────────────────────────────────────────┐  ║
║ │ Manual Classification:                                    │  ║
║ │ ○ Accela    ○ EnerGov    ○ eTRAKiT    ○ Tyler           │  ║
║ │ ○ OpenGov   ● Custom     ○ Unknown                       │  ║
║ │                                                           │  ║
║ │ Access Type:                                              │  ║
║ │ ○ Public API    ● UI-Only    ○ Open Data    ○ Custom    │  ║
║ │                                                           │  ║
║ │ Notes: [Legacy custom PHP system, scraping required]     │  ║
║ │                                                           │  ║
║ │ [Approve & Next (60s)] [Skip] [Flag for Research]        │  ║
║ └──────────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════════╝
```

**60-Second Review Goal:**
- View portal + evidence
- Select correct platform from dropdown
- Choose access type
- Add brief notes
- Approve → moves to next

**Quality Assurance:**
- Edge cases get manual attention
- Automation handles routine detections
- Result: High-quality county database

---

### Platform Distribution & Integration Strategy

**Florida County Platform Breakdown (Estimated):**

| Platform | Counties | % Coverage | API Available | Integration Effort | Priority |
|----------|----------|-----------|---------------|-------------------|----------|
| **Accela** | 25-30 | 40-45% | ✅ Yes (V4 REST) | ✅ **Complete (V1)** | N/A |
| **EnerGov** | 10-15 | 15-22% | 🔧 Yes (Tyler API) | 🔨 Medium (8-12 weeks) | **High** |
| **Custom/Legacy** | 15-20 | 22-30% | ❌ No (scraping) | 🔨 High (per-county basis) | Medium |
| **Tyler (other)** | 5-10 | 7-15% | 🔧 Varies | 🔨 Medium-High | Medium |
| **eTRAKiT** | 3-5 | 4-7% | 🔧 Limited | 🔨 Medium | Low |
| **OpenGov** | 2-4 | 3-6% | 📊 Open Data | 🔨 Low (direct CSV/API) | Low |
| **Unknown** | 2-3 | 3-4% | ❓ Unknown | 🔨 Research required | Low |

**Integration Strategy Per Platform:**

#### Accela (✅ Complete - V1)
- **Status:** Production-ready
- **Approach:** AccelaClient with OAuth refresh token flow
- **Effort:** 0 weeks (done)
- **Coverage:** Immediate access to 25-30 counties

#### EnerGov (🚧 V2 - High Priority)
- **Status:** Not implemented
- **Approach:**
  1. Tyler Technologies API documentation review
  2. Build `EnerGovAdapter` implementing same interface as `AccelaClient`
  3. OAuth flow + endpoint mapping
  4. Pilot with 1-2 counties
- **Effort:** 8-12 weeks (API integration + testing)
- **Coverage:** Adds 10-15 counties (15-22% increase)
- **ROI:** High (second-largest platform)

#### Custom/Legacy Systems (🚧 V2 - Medium Priority)
- **Status:** Not implemented
- **Approach:**
  1. Group counties by common patterns (shared vendors, similar UIs)
  2. Build web scrapers using Playwright/Selenium
  3. Implement per-county adapters as needed
  4. Fallback: Manual data entry for 1-2 truly unique systems
- **Effort:** 12-20 weeks (highly variable)
- **Coverage:** Adds 15-20 counties (22-30% increase)
- **Risk:** High maintenance burden (UIs change)

#### Tyler Tech (Other Products) (🚧 V2 - Medium Priority)
- **Status:** Not implemented
- **Approach:** Research Tyler's product portfolio, identify common APIs
- **Effort:** 6-10 weeks
- **Coverage:** Adds 5-10 counties (7-15%)

#### eTRAKiT (🚧 V2 - Low Priority)
- **Status:** Not implemented
- **Approach:** eTRAKiT API documentation + adapter
- **Effort:** 4-8 weeks
- **Coverage:** Adds 3-5 counties (4-7%)
- **ROI:** Low (small coverage gain)

#### OpenGov (🚧 V2 - Low Priority)
- **Status:** Not implemented
- **Approach:** Direct CSV/JSON downloads from open data portals (simplest integration)
- **Effort:** 2-4 weeks
- **Coverage:** Adds 2-4 counties (3-6%)
- **ROI:** Medium (easy wins)

---

### Technical Architecture (V2)

**New Backend Services:**

```python
# backend/app/services/discovery_service.py
class PermitPortalDiscoveryService:
    """Web crawler to find county permit portals."""

    async def discover_county_portal(self, county_name: str, state: str) -> DiscoveryResult:
        """
        Find official permit portal URL for a county.
        Returns: URL, source page, redirect chain, confidence score
        """
        pass

# backend/app/services/fingerprinting_service.py
class PlatformFingerprintingService:
    """Identifies permit platform from portal URL/HTML."""

    PLATFORM_SIGNATURES = {
        'accela': [...],
        'energov': [...],
        # etc.
    }

    async def fingerprint_platform(self, portal_url: str) -> FingerprintResult:
        """
        Analyze portal and return platform ID + confidence.
        Returns: platform, confidence, evidence, access_type
        """
        pass

# backend/app/services/integrations/base_adapter.py
class PermitPlatformAdapter(ABC):
    """Abstract base for all permit platform integrations."""

    @abstractmethod
    async def authenticate(self, credentials: dict) -> bool:
        pass

    @abstractmethod
    async def get_permits(self, date_from: date, date_to: date, **filters) -> List[Permit]:
        pass

    @abstractmethod
    async def get_permit_details(self, permit_id: str) -> PermitDetails:
        pass

# backend/app/services/integrations/accela_adapter.py
class AccelaAdapter(PermitPlatformAdapter):
    """Accela-specific implementation (wraps existing AccelaClient)."""
    pass

# backend/app/services/integrations/energov_adapter.py
class EnerGovAdapter(PermitPlatformAdapter):
    """EnerGov/Tyler-specific implementation."""
    pass
```

**New Database Tables:**

```sql
-- database/migrations/016_create_platform_detections.sql
CREATE TABLE platform_detections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_id UUID REFERENCES counties(id),
    detected_platform TEXT,  -- 'accela', 'energov', 'custom', etc.
    confidence_score DECIMAL(3,2),  -- 0.00-1.00
    evidence JSONB,  -- Array of detection signals
    detection_method TEXT,  -- 'automated', 'manual_review'
    reviewed_by TEXT,  -- User who reviewed (if manual)
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE platform_review_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_id UUID REFERENCES counties(id),
    portal_url TEXT,
    detected_platform TEXT,
    confidence_score DECIMAL(3,2),
    evidence JSONB,
    status TEXT DEFAULT 'pending',  -- 'pending', 'approved', 'corrected', 'flagged'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Enhanced Counties Table:**

```sql
-- Add columns to existing counties table
ALTER TABLE counties ADD COLUMN platform TEXT;  -- 'accela', 'energov', etc.
ALTER TABLE counties ADD COLUMN access_type TEXT;  -- 'api', 'ui_only', 'open_data', 'custom'
ALTER TABLE counties ADD COLUMN portal_url TEXT;
ALTER TABLE counties ADD COLUMN integration_notes TEXT;
```

---

### UI Enhancements (V2)

**Platform Detection Dashboard:**

```
╔════════════════════════════════════════════════════════════════════╗
║ Florida County Platform Detection Status                          ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║ Progress: 67/67 counties (100%) ✅                                 ║
║                                                                    ║
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ Platform      Counties  %     Auto  Manual  Review  Integrated │ ║
║ ├────────────────────────────────────────────────────────────────┤ ║
║ │ Accela        28        42%   23    5       0       28 ✅      │ ║
║ │ EnerGov       14        21%   10    4       0       0 🚧       │ ║
║ │ Custom        18        27%   0     18      0       0 🚧       │ ║
║ │ Tyler (other) 4         6%    2     2       0       0 🚧       │ ║
║ │ eTRAKiT       2         3%    1     1       0       0 🚧       │ ║
║ │ OpenGov       1         1%    1     0       0       0 🚧       │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
║                                                                    ║
║ Review Queue: 0 pending                                            ║
║                                                                    ║
║ [Run Detection] [View All Counties] [Export CSV]                  ║
╚════════════════════════════════════════════════════════════════════╝
```

**State Configuration Tab (Replaces "Add County"):**

```
╔════════════════════════════════════════════════════════════════════╗
║ State & County Configuration                                      ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║ Select State: [Florida ▼]                                         ║
║                                                                    ║
║ ┌────────────────────────────────────────────────────────────────┐ ║
║ │ County           Platform    Access      Status                │ ║
║ ├────────────────────────────────────────────────────────────────┤ ║
║ │ ✅ Hillsborough  Accela      Public API  Connected (3.2k)     │ ║
║ │ 🔧 Orange        EnerGov     Public API  Not Configured       │ ║
║ │ 🔧 Miami-Dade    Accela      Public API  Not Configured       │ ║
║ │ 🔧 Pinellas      Accela      Public API  Not Configured       │ ║
║ │ ⚠️  Sarasota     Custom      UI-Only     Manual Review Needed │ ║
║ │ ... (62 more counties)                                         │ ║
║ └────────────────────────────────────────────────────────────────┘ ║
║                                                                    ║
║ [Configure Selected Counties] [Run Platform Detection]            ║
╚════════════════════════════════════════════════════════════════════╝
```

---

### 12-Week Rollout Plan (V2)

**Phase 1: Foundation (Weeks 1-3)**
- Week 1: Design adapter interface, database schema
- Week 2: Build discovery service + fingerprinting service
- Week 3: Create review UI + queue management

**Phase 2: EnerGov Integration (Weeks 4-7)**
- Week 4: Tyler API research + OAuth setup
- Week 5: Build EnerGovAdapter
- Week 6: Pilot with 2 counties (test data pulls)
- Week 7: Rollout to all 10-15 EnerGov counties

**Phase 3: Open Data & Simple Integrations (Weeks 8-9)**
- Week 8: OpenGov adapter + direct CSV importers
- Week 9: Test with 3-5 counties

**Phase 4: Custom Systems (Weeks 10-12)**
- Week 10: Build Playwright-based scrapers for top 3 custom portals
- Week 11: Group similar custom systems, create adapters
- Week 12: QA, documentation, launch V2

**Result:** 100% Florida coverage (or 95%+ with manual fallback for 1-2 truly unique counties)

---

### Success Metrics

**Coverage Metrics:**
- ✅ **100% Detection:** All 67 counties classified
- ✅ **≥50% API Access:** At least 33 counties via public APIs
- ✅ **≥95% Integrated:** At most 3 counties require manual processes

**Quality Metrics:**
- ✅ **<10% False Positives:** Platform detection accuracy ≥90%
- ✅ **<5% Review Queue Backlog:** Human review completes within 48 hours

**Business Metrics:**
- ✅ **3-5x Lead Volume:** Increase from ~28 counties (Accela) to 67 counties (all platforms)
- ✅ **Geographic Coverage:** Every Florida market accessible to contractors
- ✅ **ROI Positive:** V2 development cost < 6 months of additional subscription revenue

---

### Why This Matters

**For HVAC Contractors:**
- **No Geographic Limits:** Target any Florida market with aging HVAC systems
- **Competitive Advantage:** Access leads competitors can't find (non-Accela counties)
- **Complete Market View:** See total addressable market (TAM) across entire state

**For Platform Business:**
- **Defensible Moat:** Comprehensive coverage harder for competitors to replicate
- **Pricing Power:** "Complete Florida coverage" justifies premium pricing
- **Scalability:** Same approach extends to other states (California, Texas, etc.)

**Market Expansion Path:**
1. **V1:** Prove ROI with Accela counties (25-30 counties, ~40% coverage)
2. **V2:** Achieve 100% Florida coverage (all 67 counties)
3. **V3:** Expand to California (58 counties), Texas (254 counties), etc.

---

### Decision Criteria: When to Build V2

**Build V2 When:**
✅ V1 Accela counties generating consistent monthly revenue
✅ Contractors requesting specific non-Accela counties by name
✅ Churn analysis shows "limited coverage" as top cancellation reason
✅ Sales team reports losing deals to "we need County X" objections
✅ Have budget for 12-week development cycle + ongoing maintenance

**Postpone V2 If:**
❌ V1 counties not yet at 50%+ utilization (focus on adoption first)
❌ Contractors satisfied with current Accela coverage
❌ Core features (scoring, CRM sync) still need improvement
❌ Platform stability/reliability issues unresolved

**Hybrid Approach:**
Start with 2-3 high-demand non-Accela counties (e.g., Orange County if EnerGov) as proof-of-concept before full 67-county rollout.

---

### NOT IMPLEMENTING YET

**This entire section describes V2 functionality that does NOT exist in the current system.**

**V1 Status (Current):**
- ✅ Accela integration complete
- ✅ Single county configuration (manual, one-by-one)
- ✅ 25-30 Florida counties accessible now

**V2 Status (Future):**
- ❌ Platform detection: Not implemented
- ❌ Multi-platform adapters: Not implemented
- ❌ Automated county discovery: Not implemented
- ❌ Review queue UI: Not implemented

**To Implement V2:** Follow 12-week rollout plan above + decision criteria.

---

## 🤝 Contributing

This is a proprietary project for HVAC contractor lead generation. All rights reserved.

## 📞 Support

For questions or issues:
- Check relevant README files in subdirectories
- Review API documentation at `/docs` endpoint
- Consult design document: `docs/plans/2025-11-28-hvac-lead-gen-design.md`

## 📜 License

Proprietary - All rights reserved

---

**Built with ❤️ for HVAC contractors looking to grow their replacement business**
