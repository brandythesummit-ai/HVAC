# ⚠️ SECURITY REMINDER

## Deployment Protection Currently DISABLED

**Status**: Vercel deployment protection is currently turned OFF.

**Action Required**: Re-enable deployment protection BEFORE launching to production users.

### When to Re-Enable Protection

Re-enable when you implement authentication in the application:
1. Add user login/authentication to the frontend
2. Configure proper access controls
3. Re-enable Vercel deployment protection

### How to Re-Enable Protection

**Via Vercel Dashboard:**
1. Go to https://vercel.com/brandy-sommers-projects/hvac/settings/deployment-protection
2. Enable "Vercel Authentication" for appropriate deployment types
3. Choose protection level:
   - `preview` - Only preview deployments (recommended)
   - `all` - All deployments including production
   - `prod_deployment_urls_and_all_previews` - Production URLs + previews

**Via API:**
```bash
curl -X PATCH "https://api.vercel.com/v9/projects/prj_kIwrbJyOHOyvxokNWR6e0gUyousf?teamId=team_mXNojDGZmNo45m5gU2Q39r6V" \
  -H "Authorization: Bearer $VERCEL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ssoProtection": {"deploymentType": "preview"}}'
```

**Recommended**: Enable protection for `preview` deployments only, keeping production domains public.

## Current Configuration

- **Protection Level**: None (disabled)
- **Date Disabled**: November 28, 2025
- **Reason**: Development convenience - to access deployment URLs without authentication

## Important Notes

- DO NOT launch to production users while protection is disabled
- Anyone with a deployment URL can access the site
- This is suitable ONLY for development/testing
- Re-enable before handling real user data or going live
