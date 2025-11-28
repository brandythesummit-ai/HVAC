-- Migration 005: Create sync_config table
-- This table stores sync configuration for agencies
-- Currently supports manual mode, but designed for future automation

CREATE TABLE IF NOT EXISTS sync_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,

    -- Sync Mode Configuration
    sync_mode TEXT DEFAULT 'manual' NOT NULL,  -- 'manual', 'scheduled', 'realtime' (future)
    schedule_cron TEXT,  -- Cron expression for scheduled syncs (future feature)
    is_active BOOLEAN DEFAULT true NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add comments
COMMENT ON TABLE sync_config IS 'Sync configuration for agencies (manual/scheduled/realtime modes)';
COMMENT ON COLUMN sync_config.sync_mode IS 'Sync mode: manual (current), scheduled (future), realtime (future)';
COMMENT ON COLUMN sync_config.schedule_cron IS 'Cron expression for scheduled syncs (e.g., "0 9 * * MON")';
COMMENT ON COLUMN sync_config.is_active IS 'Whether sync configuration is active';
