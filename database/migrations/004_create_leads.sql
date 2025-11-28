-- Migration 004: Create leads table
-- This table tracks which permits have been converted to leads
-- and manages sync status with The Summit.AI CRM

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    permit_id UUID NOT NULL REFERENCES permits(id) ON DELETE CASCADE,
    county_id UUID NOT NULL REFERENCES counties(id) ON DELETE CASCADE,

    -- Summit.AI Sync Management
    summit_sync_status TEXT DEFAULT 'pending' NOT NULL,  -- 'pending', 'synced', 'failed'
    summit_contact_id TEXT,  -- Contact ID in The Summit.AI (after successful sync)
    summit_synced_at TIMESTAMP WITH TIME ZONE,  -- When lead was synced
    sync_error_message TEXT,  -- Error message if sync failed

    -- Additional Notes
    notes TEXT,  -- User notes about this lead

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add comments
COMMENT ON TABLE leads IS 'Leads created from permits for syncing to The Summit.AI CRM';
COMMENT ON COLUMN leads.summit_sync_status IS 'Sync status: pending (not synced), synced (success), failed (error)';
COMMENT ON COLUMN leads.summit_contact_id IS 'The Summit.AI contact ID after successful sync';
COMMENT ON COLUMN leads.sync_error_message IS 'Error details if sync failed';
