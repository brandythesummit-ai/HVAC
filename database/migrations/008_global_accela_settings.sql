-- Migration 008: Create app_settings table for global Accela credentials
-- Part of county workflow redesign to use refresh_token OAuth flow
-- App ID and Secret are now global (shared across all counties)

-- Create app_settings table
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    app_id TEXT,
    app_secret TEXT,  -- Encrypted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Migrate existing county credentials to global (if any exist)
-- This takes the first county's credentials and makes them global
-- User should verify these are correct after migration
INSERT INTO app_settings (key, app_id, app_secret)
SELECT 'accela', accela_app_id, accela_app_secret
FROM counties
WHERE accela_app_id IS NOT NULL
  AND accela_app_secret IS NOT NULL
LIMIT 1
ON CONFLICT (key) DO NOTHING;

COMMENT ON TABLE app_settings IS 'Global application settings (Accela credentials, etc.)';
COMMENT ON COLUMN app_settings.key IS 'Setting key (e.g., "accela")';
COMMENT ON COLUMN app_settings.app_id IS 'Accela Application ID (shared across all counties)';
COMMENT ON COLUMN app_settings.app_secret IS 'Accela Application Secret (encrypted, shared across all counties)';
