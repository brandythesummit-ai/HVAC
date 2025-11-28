# GoHighLevel Private Integration Setup Guide

This guide will help you set up GoHighLevel Private Integration with THE Summit.ai HVAC Lead Generation platform.

## What is a Private Integration?

**Private Integrations** are static/fixed access tokens that allow you to build custom integrations between your HighLevel account and third-party applications. They're simpler than public marketplace apps because they use a single, long-lived access token instead of OAuth flows.

## How It Works

1. You create a Private Integration in your GHL Agency Settings
2. GHL generates a **static access token** (format: `pit-****-****-****-****`)
3. You copy this token **once** (you can't retrieve it again later)
4. Paste the token into your application settings
5. The application uses it to make API calls to GHL

## Setup Steps

### Step 1: Create a Private Integration in GHL

1. Log into your GoHighLevel account
2. Go to **Settings** → **Integrations** → **Private Integrations**
   - If you don't see this option, enable it in **Settings** → **Labs**
3. Click **"Create New Integration"**
4. Fill in the details:
   - **Name**: "HVAC Lead Gen Platform" (or whatever helps you identify it)
   - **Description**: "Integration for HVAC permit lead generation"
5. Select the **scopes** (permissions) your integration needs:
   - ✅ `contacts.readonly` - Read contact information
   - ✅ `contacts.write` - Create and update contacts
   - ✅ `locations.readonly` - Read location information
6. Click **"Create"**
7. **IMPORTANT**: Copy the access token immediately - you won't be able to see it again!
   - Format: `pit-****-****-****-****`

### Step 2: Get Your Location ID

1. In your GHL account, go to the location you want to integrate with
2. Look at the URL - it will contain your Location ID
   - Example: `https://app.gohighlevel.com/location/ABC123XYZ/dashboard`
   - Your Location ID is: `ABC123XYZ`

### Step 3: Configure Your Application

#### Option A: Using the Web Interface (Recommended)

1. Start your backend server:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

2. Start your frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Open your browser and go to the Settings page
4. In the "Summit.AI Configuration" section:
   - Paste your **Access Token** (pit-****-****-****-****)
   - Enter your **Location ID**
5. Click **"Save Settings"**
6. Click **"Test Connection"** to verify it works

#### Option B: Using Environment Variables

1. Edit `backend/.env`:
   ```env
   SUMMIT_ACCESS_TOKEN=pit-your-actual-token-here
   SUMMIT_LOCATION_ID=your-location-id-here
   ```

2. Restart your backend server

### Step 4: Verify Connection

After configuration, test the connection:

1. In the Settings page, click **"Test Connection"**
2. You should see "Connection successful"
3. If you get an error, double-check:
   - Token is copied correctly (no extra spaces)
   - Location ID is correct
   - Scopes include the required permissions

## Token Management

### Token Rotation

GHL allows you to rotate your access token for security:

1. Go to your Private Integration in GHL Settings
2. Click **"Rotate and expire this token later"** or **"Rotate and expire this token now"**
3. **7-day grace period**: If you choose "later", both old and new tokens work for 7 days
4. Update your application with the new token before the old one expires

### Auto-Expiry

Private Integration tokens automatically expire if **not used for 90 days**. To prevent this:
- Make sure your application is actively syncing leads
- Or manually test the connection every few months

### If Your Token is Compromised

1. Immediately go to GHL Settings → Private Integrations
2. Click **"Rotate and expire this token now"**
3. Copy the new token
4. Update your application with the new token
5. The old token will stop working immediately

## Security Best Practices

1. **Never commit tokens to git**
   - The `.env` file is in `.gitignore` - keep it that way
   - Use `.env.example` for documentation only

2. **Limit scopes**
   - Only grant permissions your application actually needs
   - Don't use `*.write` if you only need to read data

3. **Rotate regularly**
   - Consider rotating your token every 90 days for security
   - Use the 7-day grace period to avoid downtime

4. **Monitor usage**
   - Check GHL's API logs to detect unusual activity
   - If you see unexpected API calls, rotate your token immediately

## Troubleshooting

### "No access token configured"
- You haven't entered your token yet
- Go to Settings and paste your Private Integration token

### "Connection failed: 401 Unauthorized"
- Your token is invalid or expired
- Generate a new token in GHL and update your app

### "Connection failed: 403 Forbidden"
- Your token doesn't have the required scopes
- Recreate your Private Integration with the correct permissions:
  - `contacts.readonly`
  - `contacts.write`
  - `locations.readonly`

### "Connection failed: 404 Not Found"
- Your Location ID is incorrect
- Double-check the Location ID from your GHL URL

## API Details

### Base URL
```
https://services.leadconnectorhq.com
```

### Authentication Header
```
Authorization: Bearer pit-****-****-****-****
```

### Required Scopes
- `contacts.readonly` - Search for existing contacts
- `contacts.write` - Create and update contacts
- `locations.readonly` - Verify location access

## Additional Resources

- [GHL Private Integrations Documentation](https://help.gohighlevel.com/support/solutions/articles/155000003054-private-integrations-everything-you-need-to-know)
- [GHL API Documentation](https://marketplace.gohighlevel.com/docs/Authorization/PrivateIntegrationsToken/)
- [GHL Developer Portal](https://marketplace.gohighlevel.com/docs/)

## Need Help?

If you encounter issues:
1. Check the troubleshooting section above
2. Verify your token and location ID are correct
3. Review GHL's API logs for error details
4. Contact support with specific error messages

---

**Note**: Private Integrations are for internal use only. If you're building a public app for the GHL Marketplace, you'll need to use OAuth 2.0 instead (different process).
