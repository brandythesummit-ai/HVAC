# 🚀 HVAC Lead Gen - Complete Deployment Guide

Follow these steps in order to deploy your HVAC Lead Generation platform to production.

**Estimated Time:** 30-45 minutes
**Cost:** Free tier for all services (initially)

**⚠️ IMPORTANT - Current Deployment Status:**
- This guide describes deploying a production-ready V1 Accela integration
- **0 counties are currently deployed** (HCFL pilot was deleted for statewide rebuild)
- Infrastructure is validated and ready for Florida's ~25-30 Accela counties
- MVP requires all 67 Florida counties (37-42 require V2 multi-platform support - see README.md Future Vision)

---

## ✅ Prerequisites Checklist

Before you start, make sure you have:
- [ ] GitHub account
- [ ] Supabase account (create at https://supabase.com)
- [ ] Railway account (create at https://railway.app)
- [ ] Vercel account (create at https://vercel.com)
- [ ] Git installed locally
- [ ] This code committed (✅ Already done!)

---

## Phase 1: Push Code to GitHub (5 minutes)

### Step 1.1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `hvac-lead-gen` (or your choice)
3. Description: "HVAC Lead Generation Platform with Accela API"
4. Keep it **Private** (contains credentials later)
5. **Do NOT** initialize with README, .gitignore, or license
6. Click "Create repository"

### Step 1.2: Push Your Code

```bash
# Add GitHub as remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/hvac-lead-gen.git

# Push to GitHub
git push -u origin main
```

**Verify:** Go to your GitHub repo and confirm all files are there.

---

## Phase 2: Set Up Supabase Database (10 minutes)

### Step 2.1: Create Supabase Project

1. Go to https://supabase.com/dashboard
2. Click "New project"
3. Choose organization (or create one)
4. **Project name:** `hvac-lead-gen`
5. **Database password:** Generate a strong password (SAVE THIS!)
6. **Region:** Choose closest to you
7. Click "Create new project" (takes ~2 minutes)

### Step 2.2: Run Database Migrations

**Option A: Using Supabase Dashboard (Easiest)**

1. In your Supabase project, go to **SQL Editor** (left sidebar)
2. Click **New query**
3. Open `/Users/Brandy/projects/HVAC/database/migrations/001_create_agencies.sql`
4. Copy and paste the content
5. Click **Run**
6. Repeat for migrations 002, 003, 004, 005, 006 in order

**Option B: Using Command Line**

```bash
cd /Users/Brandy/projects/HVAC/database

# Get your connection string from Supabase Dashboard → Settings → Database
export DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Run migrations
./run_migrations.sh
```

### Step 2.3: (Optional) Load Test Data

In Supabase SQL Editor:
1. Open `/Users/Brandy/projects/HVAC/database/seed.sql`
2. Copy and paste the content
3. Click **Run**

This creates sample data for testing.

### Step 2.4: Get Supabase Credentials

In Supabase Dashboard → **Settings** → **API**:

Copy these values (you'll need them later):
- **Project URL:** `https://xxxxx.supabase.co`
- **Anon public key:** `eyJhbGc...` (starts with eyJ)
- **Service role key:** `eyJhbGc...` (different from anon key)

**Save these in a secure note!**

---

## Phase 3: Deploy Backend to Railway (10 minutes)

### Step 3.1: Create Railway Account

1. Go to https://railway.app
2. Sign in with GitHub
3. Authorize Railway to access your repositories

### Step 3.2: Create New Project

1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your `hvac-lead-gen` repository
4. Railway will detect it's a monorepo

### Step 3.3: Configure Backend Service

1. Click "Add a service"
2. Select "GitHub Repo"
3. In the service settings:
   - **Root Directory:** `/backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 3.4: Add Environment Variables

In Railway, go to your service → **Variables** tab:

Click "Raw Editor" and paste:

```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
CORS_ORIGINS=*
ENCRYPTION_KEY=your_32_byte_encryption_key_here_must_be_at_least_32_chars
```

**To generate ENCRYPTION_KEY:**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step 3.5: Deploy

1. Railway will automatically deploy
2. Wait for build to complete (~2-3 minutes)
3. Once deployed, click "Settings" → "Generate Domain"
4. Copy your backend URL (e.g., `https://hvac-backend.railway.app`)

**Test it:** Visit `https://your-backend-url.railway.app/health`
Should return: `{"status": "healthy"}`

---

## Phase 4: Deploy Frontend to Vercel (10 minutes)

### Step 4.1: Create Vercel Account

1. Go to https://vercel.com/signup
2. Sign in with GitHub
3. Authorize Vercel

### Step 4.2: Import Project

1. Click "Add New..." → "Project"
2. Import your `hvac-lead-gen` repository
3. Vercel will detect it's a monorepo

### Step 4.3: Configure Frontend

In the import settings:

- **Framework Preset:** Vite
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`

### Step 4.4: Add Environment Variable

Click "Environment Variables" and add:

- **Key:** `VITE_API_URL`
- **Value:** `https://your-backend-url.railway.app` (from Phase 3)

### Step 4.5: Deploy

1. Click "Deploy"
2. Wait for build (~2-3 minutes)
3. Once deployed, Vercel will give you a URL (e.g., `https://hvac-lead-gen.vercel.app`)

**Test it:** Visit your Vercel URL - you should see the frontend!

---

## Phase 5: Final Configuration (5 minutes)

### Step 5.1: Update CORS in Backend

Go back to Railway → Your backend service → Variables:

Update `CORS_ORIGINS`:
```
CORS_ORIGINS=https://hvac-lead-gen.vercel.app,https://hvac-lead-gen-*.vercel.app
```

(Replace with your actual Vercel domain)

Railway will automatically redeploy.

### Step 5.2: Create Initial Agency

**Option A: Using Supabase Dashboard**

1. Go to Supabase → Table Editor → `agencies`
2. Click "Insert" → "Insert row"
3. Fill in:
   - `name`: Your business name
   - `summit_api_key`: (leave blank for now)
   - `summit_location_id`: (leave blank for now)
4. Click "Save"
5. Copy the generated `id` (UUID)

**Option B: Using SQL Editor**

```sql
INSERT INTO agencies (name)
VALUES ('Your HVAC Business Name')
RETURNING id;
```

Copy the returned ID.

### Step 5.3: Test the Application

1. Open your Vercel URL: `https://your-app.vercel.app`
2. You should see the Counties page
3. Try clicking "Add County" - the modal should open
4. Check browser console for any errors

---

## Phase 6: Get Your API Credentials

### Step 6.1: Get Summit.AI (HighLevel) API Key

1. Log into your HighLevel account
2. Go to **Settings** → **Integrations** → **API Keys**
3. Click "Create API Key"
4. Name it "HVAC Lead Gen"
5. Copy the API key (starts with `pk_...` or similar)
6. Also copy your **Location ID** (Settings → Business Profile)

### Step 6.2: Add Summit.AI Credentials

**In the Frontend:**
1. Go to your deployed app
2. Click "Settings" in the navigation
3. Paste your Summit.AI API Key
4. Paste your Location ID
5. Click "Test Connection"
6. If successful, click "Save"

**OR in Supabase:**
```sql
UPDATE agencies
SET summit_api_key = 'your_api_key',
    summit_location_id = 'your_location_id'
WHERE id = 'your_agency_id';
```

### Step 6.3: Get Accela Credentials

You'll need to contact each county to get Accela API credentials:

1. Contact your county's building department
2. Ask for Accela API access
3. They'll provide:
   - **Environment URL:** (e.g., `https://apis.accela.com`)
   - **App ID**
   - **App Secret**
   - **Agency name/code**

**NOTE:** Some counties charge for API access. Check with them first.

---

## Phase 7: Test End-to-End (10 minutes)

### Step 7.1: Add Your First County

1. Go to your deployed app → Counties page
2. Click "Add County"
3. **Step 1:** Enter county name (e.g., "Hillsborough County, FL")
4. **Step 2:** Enter Accela credentials
   - Environment: `https://apis.accela.com` (or county-specific)
   - App ID: From county
   - App Secret: From county
5. **Step 3:** Test connection
   - If successful, click "Save County"
   - If failed, check credentials

### Step 7.2: Pull Some Permits

1. Click "Pull Permits" on your county card
2. Set date range (example - not hardcoded, dates calculated dynamically):
   - Start: `2010-01-01` (or use rolling 30-year window: current_year - 30)
   - End: `2015-12-31` (or current date)
3. Max results: `50`
4. Check "Finaled only"
5. Click "Pull Permits"
6. Wait for the process to complete

**What happens:**
- Backend calls Accela API with `type='Building/Residential/Trade/Mechanical'` parameter (API-level filtering)
- Only HVAC permits returned (more efficient than pulling all Building permits and filtering client-side)
- Enriches with property data (parcels, owners, addresses)
- Stores in database with full raw_data JSONB

**Note:** All date ranges are calculated dynamically. The system never hardcodes dates - it uses rolling windows (e.g., 30-year historical pull = current_year - 30).

### Step 7.3: View Leads

1. Go to "Leads" page
2. You should see the pulled permits as leads
3. Check that property data is populated:
   - Address
   - Year built
   - Square footage
   - Owner name

### Step 7.4: Sync to Summit.AI

1. Select a few leads (checkboxes)
2. Click "Send to Summit.AI"
3. Watch the sync status change:
   - 🟡 Pending → ✅ Synced

4. **Verify in Summit.AI:**
   - Log into HighLevel
   - Go to Contacts
   - Search for the owner name
   - Confirm the contact was created with custom fields

---

## 🎉 Deployment Complete!

Your HVAC Lead Generation platform is now **fully deployed** and operational!

### Your Deployment URLs

- **Frontend:** https://your-app.vercel.app
- **Backend:** https://your-backend.railway.app
- **Database:** Supabase (managed)
- **Swagger Docs:** https://your-backend.railway.app/docs

### Next Steps

1. **Add more counties** - MVP requires all 67 Florida counties:
   - ~25-30 Accela counties can be configured immediately using this V1 integration
   - Remaining 37-42 counties require V2 multi-platform support (see README.md Future Vision)
   - Each county repeats the Accela API credential process above
2. **Set up monitoring** - Railway and Vercel have built-in logs
3. **Configure custom domain** - Add your own domain in Vercel settings
4. **Set up alerts** - Monitor for failed syncs or API errors
5. **Create workflows** - Set up Summit.AI automation workflows for leads

---

## Troubleshooting

### Frontend shows "Network Error"

- Check that `VITE_API_URL` is set correctly in Vercel
- Verify CORS is configured in Railway backend
- Check Railway logs for errors

### Backend deployment fails

- Check Railway logs
- Verify `requirements.txt` is in `/backend` folder
- Ensure Python version is compatible (3.11+)

### Database connection fails

- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Check Supabase is not paused (free tier pauses after inactivity)
- Verify migrations ran successfully

### Accela API returns "Invalid token"

- Check credentials are correct
- Verify token hasn't expired (backend should auto-refresh)
- Confirm authorization header format (NO "Bearer " prefix)

### Summit.AI sync fails

- Check API key is valid and not expired
- Verify Location ID is correct
- Check contact has required fields (phone or email)
- Review error message in lead details

---

## Cost Breakdown (Free Tier Limits)

| Service | Free Tier | Upgrade Needed When |
|---------|-----------|---------------------|
| **Supabase** | 500MB database, 2GB bandwidth | >500MB data or >2GB/month traffic |
| **Railway** | $5 credit/month, ~500 hours | Usage exceeds $5/month |
| **Vercel** | 100GB bandwidth, unlimited sites | >100GB/month or need team features |
| **Total** | ~$5/month Railway credit | You start growing! |

**Estimated monthly cost at scale:** $20-50/month
(Covers Railway backend, Supabase Pro, Vercel Pro if needed)

---

## Support

If you run into issues:

1. Check the logs:
   - **Backend:** Railway dashboard → Service → Deployments → Logs
   - **Frontend:** Vercel dashboard → Project → Deployments → Logs
   - **Database:** Supabase dashboard → Logs

2. Review documentation:
   - Backend: `/backend/README.md`
   - Frontend: `/frontend/README.md`
   - Database: `/database/README.md`

3. Test locally first:
   - Follow local development guide in each README
   - Verify everything works locally before debugging deployment

---

## Security Checklist

Before going to production:

- [ ] Change all default passwords
- [ ] Rotate ENCRYPTION_KEY if exposed
- [ ] Enable Supabase Row Level Security (RLS)
- [ ] Set up Supabase backups
- [ ] Restrict CORS to specific domains (not `*`)
- [ ] Enable Railway/Vercel deploy protection
- [ ] Review API rate limits
- [ ] Set up monitoring and alerts
- [ ] Create a separate Accela test account for development

---

## Congratulations! 🎊

You've successfully deployed a production-ready HVAC lead generation platform!

Your system can now:
- ✅ Pull HVAC permits from multiple counties
- ✅ Enrich permits with property data
- ✅ Manage leads in a beautiful dashboard
- ✅ Sync leads to The Summit.AI CRM
- ✅ Handle token refresh automatically
- ✅ Scale to unlimited counties

**Happy lead hunting!** 🏠🔧
