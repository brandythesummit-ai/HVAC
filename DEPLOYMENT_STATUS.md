# HVAC Lead Gen - Deployment Status
**Last Updated:** 2025-11-28
**Status:** ✅ FULLY DEPLOYED AND WORKING

## Current Situation

### What's Working ✅
- **Frontend**: Successfully deployed to Vercel
  - URL: https://hvac-liard.vercel.app
  - Build: Passing
  - Framework: Vite + React
  - VITE_API_URL: Configured to Railway backend

- **Backend**: Successfully deployed to Railway
  - URL: https://hvac-backend-production-11e6.up.railway.app
  - Status: Healthy
  - All API endpoints working correctly

- **Supabase**: Database configured and connected
  - URL: https://jlammryvteuhrlygpqif.supabase.co
  - Tables: agencies, counties, permits, leads
  - Authentication: Working

### Issue Resolution ✅
- **Root Cause**: Typo in Supabase project reference
  - Incorrect: `jlammryvteuhrlyepqif` (with 'e')
  - Correct: `jlammryvteuhrlygpqif` (with 'g')
  - Both SUPABASE_URL and SUPABASE_KEY had the typo
  - **Fixed**: Updated both environment variables in Railway

## Root Cause Analysis

### Issue Details
1. **Frontend API Configuration** (frontend/src/api/client.js:3)
   ```javascript
   const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
   ```
   - `VITE_API_URL` not set in Vercel → defaults to localhost
   - Browser can't reach localhost from deployed app → Network Error

2. **Backend Not Deployed**
   - No Railway deployment
   - No Vercel serverless functions
   - Backend code exists locally but not hosted anywhere

3. **Environment Variables Missing**
   - Vercel frontend: Missing `VITE_API_URL`
   - Railway backend: Needs all vars from `vercel-backend.env`

## Next Steps: Railway Deployment

### Step 1: Deploy Backend to Railway
Use Railway MCP to:
1. Create new Railway project named "hvac-backend"
2. Connect to GitHub repo (brandythesummit-ai/HVAC)
3. Set root directory to `/backend`
4. Configure Python buildpack
5. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 2: Configure Railway Environment Variables
Add ALL variables from `vercel-backend.env`:
```bash
SUPABASE_URL=https://jlammryvteuhrlygpqif.supabase.co
SUPABASE_KEY=<your-supabase-anon-key>
ENCRYPTION_KEY=jkYMzeybIKViHfSg2C8jChxh7OnanInvcTH6EOgOMG8=
CORS_ORIGINS=https://hvac-liard.vercel.app,http://localhost:3000,http://localhost:5173
ENVIRONMENT=production
```

**Important**: Update `CORS_ORIGINS` to include all Vercel preview URLs:
```
CORS_ORIGINS=https://hvac-liard.vercel.app,https://hvac-*.vercel.app,http://localhost:5173
```

### Step 3: Get Railway Backend URL
After deployment, Railway will provide a URL like:
- `https://hvac-backend-production.up.railway.app`

Test the health endpoint:
```bash
curl https://your-railway-url.railway.app/health
```

Expected response:
```json
{"status": "healthy", "environment": "production"}
```

### Step 4: Configure Vercel Frontend Environment Variable
Add to Vercel project settings:
- **Key**: `VITE_API_URL`
- **Value**: `https://your-railway-url.railway.app`
- **Environments**: Production, Preview, Development

### Step 5: Redeploy Vercel Frontend
- Trigger new deployment on Vercel
- Or use: Vercel dashboard → Deployments → Latest → Redeploy

### Step 6: Test Complete Flow
1. **Health Check**: `GET https://railway-url/health` → 200 OK
2. **Counties Page**: Visit Vercel URL → Should load without errors
3. **Leads Page**: Should load without errors
4. **Settings Page**: Should load without errors
5. **Browser Console**: Check for no network errors

## Verification Checklist

After deployment, verify:
- [ ] Railway backend is running and accessible
- [ ] `/health` endpoint returns 200 OK
- [ ] Vercel frontend has `VITE_API_URL` configured
- [ ] CORS allows Vercel domain
- [ ] Counties page loads without "Network Error"
- [ ] Leads page loads without "Network Error"
- [ ] Settings page loads without "Network Error"
- [ ] Browser DevTools shows API calls to Railway URL
- [ ] No CORS errors in console

## Environment Variables Reference

### Railway Backend (All Required)
| Variable | Value | Source |
|----------|-------|--------|
| SUPABASE_URL | https://jlammryvteuhrlygpqif.supabase.co | vercel-backend.env |
| SUPABASE_KEY | <your-supabase-anon-key> | vercel-backend.env |
| ENCRYPTION_KEY | jkYMzeybI... (see file) | vercel-backend.env |
| CORS_ORIGINS | https://hvac-*.vercel.app,... | vercel-backend.env (update) |
| ENVIRONMENT | production | vercel-backend.env |
| API_HOST | 0.0.0.0 | Default OK |
| API_PORT | $PORT | Railway provides this |

### Vercel Frontend (Required)
| Variable | Value | Source |
|----------|-------|--------|
| VITE_API_URL | https://[railway-url] | From Railway deployment |

## Troubleshooting

### If "Network Error" Persists After Deployment
1. Check browser DevTools → Network tab → What URL is it calling?
2. Verify `VITE_API_URL` is set in Vercel (Settings → Environment Variables)
3. Verify Vercel redeployed after adding env var
4. Test Railway backend directly: `curl https://railway-url/health`
5. Check Railway logs for errors
6. Verify CORS_ORIGINS includes Vercel domain

### If CORS Errors Appear
- Railway env var `CORS_ORIGINS` must include exact Vercel domain
- Format: `https://hvac-liard.vercel.app,https://hvac-*.vercel.app`
- No trailing slashes, comma-separated

### If Backend Health Check Fails
- Check Railway deployment logs
- Verify all environment variables are set
- Check Railway buildpack detected Python correctly
- Verify start command is correct

## Project Info

### Vercel
- **Team ID**: team_mXNojDGZmNo45m5gU2Q39r6V
- **Project ID**: prj_kIwrbJyOHOyvxokNWR6e0gUyousf
- **Production URL**: https://hvac-liard.vercel.app
- **Git Repo**: github.com/brandythesummit-ai/HVAC

### Supabase
- **Project**: jlammryvteuhrlygpqif
- **Region**: US East
- **Tables**: agencies, counties, permits, leads, sync_config, properties, background_jobs, pull_history, county_pull_schedules (9 total)

### Railway (To Be Created)
- **Project Name**: hvac-backend
- **Root Directory**: /backend
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Files Reference
- Backend env template: `vercel-backend.env`
- Deployment guide: `DEPLOYMENT_GUIDE.md`
- Frontend API client: `frontend/src/api/client.js`
- Backend main: `backend/app/main.py`
- Backend config: `backend/app/config.py`

## API Endpoints Verification

All endpoints tested and working:

```bash
# Health check
curl https://hvac-backend-production-11e6.up.railway.app/health
# Response: {"status": "healthy", "environment": "production"}

# Counties endpoint
curl https://hvac-backend-production-11e6.up.railway.app/api/counties
# Response: {"success": true, "data": [], "error": null}

# Leads endpoint
curl https://hvac-backend-production-11e6.up.railway.app/api/leads
# Response: {"success": true, "data": {"leads": [], "count": 0}, "error": null}

# Summit config endpoint
curl https://hvac-backend-production-11e6.up.railway.app/api/summit/config
# Response: {"access_token": "", "location_id": "", "configured": false}
```

## Next Steps for User

The application is now fully deployed and functional. You can now:

1. **Visit the application**: https://hvac-liard.vercel.app
2. **Add counties**: Go to Counties page and click "Add County"
3. **Configure Summit.AI**: Go to Settings page and save your API keys
4. **Generate leads**: Once configured, the system will pull permit data

All pages should load without "Network Error" messages.
