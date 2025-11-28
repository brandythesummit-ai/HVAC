-- Migration 001: Create agencies table
-- This table stores HVAC contractor agencies (tenant/organization level)
-- Each agency can have multiple counties configured

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create agencies table
CREATE TABLE IF NOT EXISTS agencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    summit_api_key TEXT,  -- The Summit.AI (HighLevel) API key - will be encrypted by backend
    summit_location_id TEXT,  -- The Summit.AI location/sub-account ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add comment to table
COMMENT ON TABLE agencies IS 'HVAC contractor agencies - top level tenant/organization';
COMMENT ON COLUMN agencies.summit_api_key IS 'The Summit.AI CRM API key (encrypted by backend)';
COMMENT ON COLUMN agencies.summit_location_id IS 'The Summit.AI location ID for lead syncing';
