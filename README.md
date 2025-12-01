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

## ✨ Key Features

### 🏢 Multi-County Permit Pulling
- Connect to any county using Accela Civic Platform V4 API
- **Adaptive rate limiting** - header-based throttling prevents API account suspension
- Pull 30 years of historical HVAC permits for comprehensive lead database
- Automated daily incremental pulls to catch new installations
- Automatic pagination (handles 1,000+ permits per pull)
- API-level filtering for HVAC permits only (more efficient)

### 🏠 Property-Centric Data Model
- **Address Normalization** - Matches multiple permits to same property
- **HVAC Age Tracking** - Calculates system age from most recent permit
- **Intelligent Lead Scoring** (0-100) based on replacement urgency
- **Automatic Tiering**:
  - 🔥 **HOT (80-100):** 15-20+ years old - Replacement imminent
  - 🌡️ **WARM (60-75):** 10-15 years old - Maintenance + potential replacement
  - 🧊 **COOL (40-55):** 5-10 years old - Maintenance focus
  - ❄️ **COLD (0-35):** <5 years old - Not qualified

### 🤖 Background Job Processing
- **30-Year Historical Pulls** - Process decades of permits automatically
- **PostgreSQL-Based** - No Redis, Celery, or external dependencies
- **Real-Time Progress Tracking** - Monitor permits/second, ETA, stats
- **Automatic Retries** - Handles transient API failures
- **Graceful Cancellation** - Stop long-running jobs without data loss

### 📅 Automated Scheduling
- **Daily Incremental Pulls** - Automatically fetches new permits every 7 days
- **Hourly Checks** - Background scheduler monitors for due counties
- **Configurable Per County** - Enable/disable automation individually

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
