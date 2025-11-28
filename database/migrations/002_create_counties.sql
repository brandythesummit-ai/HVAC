-- Migration 002: Create counties table
-- This table stores county configurations with Accela API credentials
-- Each county belongs to an agency and has its own Accela environment

CREATE TABLE IF NOT EXISTS counties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,

    -- Accela API Configuration
    accela_environment TEXT NOT NULL,  -- e.g., 'PROD', 'TEST', or custom domain
    accela_app_id TEXT NOT NULL,  -- Accela app ID
    accela_app_secret TEXT NOT NULL,  -- Accela app secret - will be encrypted by backend

    -- Accela Token Management (15-minute expiration)
    accela_access_token TEXT,  -- Current OAuth access token
    token_expires_at TIMESTAMP WITH TIME ZONE,  -- Token expiration timestamp

    -- Status and Activity Tracking
    last_pull_at TIMESTAMP WITH TIME ZONE,  -- Last time permits were pulled
    status TEXT DEFAULT 'disconnected' NOT NULL,  -- 'connected', 'disconnected', 'token_expired', 'error'
    is_active BOOLEAN DEFAULT true NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add comments
COMMENT ON TABLE counties IS 'County configurations with Accela API credentials for permit pulling';
COMMENT ON COLUMN counties.accela_environment IS 'Accela environment (PROD, TEST, or custom domain)';
COMMENT ON COLUMN counties.accela_access_token IS 'Current OAuth access token (encrypted, expires every 15 minutes)';
COMMENT ON COLUMN counties.status IS 'Connection status: connected, disconnected, token_expired, error';
