-- Migration: Convert counties to use OAuth refresh tokens instead of per-county app credentials
-- Date: 2025-11-28
-- Description: Remove app_id/app_secret from counties, add county_code and refresh_token fields

-- Add new columns for OAuth flow
ALTER TABLE counties
ADD COLUMN IF NOT EXISTS county_code TEXT,
ADD COLUMN IF NOT EXISTS refresh_token TEXT,  -- Encrypted refresh token from OAuth flow
ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS oauth_state TEXT;  -- For CSRF protection during OAuth flow

-- Remove old app credential columns
ALTER TABLE counties
DROP COLUMN IF EXISTS app_id,
DROP COLUMN IF EXISTS app_secret,
DROP COLUMN IF EXISTS environment;

-- Add comment explaining the new OAuth flow
COMMENT ON COLUMN counties.refresh_token IS 'Encrypted OAuth refresh token obtained through authorization flow';
COMMENT ON COLUMN counties.county_code IS 'Accela county/agency code (e.g., "ISLANDERNC" for Nassau County)';
COMMENT ON COLUMN counties.oauth_state IS 'Temporary CSRF state token used during OAuth authorization flow';
COMMENT ON COLUMN counties.token_expires_at IS 'Timestamp when the refresh token expires';
