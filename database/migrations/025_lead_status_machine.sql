-- Migration 025: Lead status machine + cooldown bookkeeping
-- Implements the lead lifecycle from docs/design/2026-04-21-post-pivot-design.md §4:
--   NEW → KNOCKED_* → (cooldown) → resurface to NEW
--   NEW → INTERESTED → APPOINTMENT_SET → QUOTED → WON / LOST
-- M12 wires the state transitions in app/services/lead_status_machine.py.

-- 1. Add status columns to leads table
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS lead_status TEXT
        NOT NULL DEFAULT 'NEW'
        CHECK (lead_status IN (
            'NEW',
            'KNOCKED_NO_ANSWER',
            'KNOCKED_SPOKE_TO_NON_DM',
            'KNOCKED_WRONG_PERSON',
            'KNOCKED_NOT_INTERESTED',
            'INTERESTED',
            'APPOINTMENT_SET',
            'QUOTED',
            'WON',
            'LOST'
        ));

ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMP WITH TIME ZONE
        DEFAULT now();

-- When a lead is put on cooldown (NOT_INTERESTED, NO_ANSWER), the
-- scheduler resurfaces it to NEW after this timestamp. NULL means
-- no cooldown pending.
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS resurface_after TIMESTAMP WITH TIME ZONE;

-- Free-text rationale for the status change (e.g., "Not interested
-- because rental", "Homeowner was at work — try evening").
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS status_note TEXT;

-- Indexes supporting common queries:
--   - the "resurface pending" cron: WHERE resurface_after < now()
--   - the map/list filter: WHERE lead_status IN (...)
CREATE INDEX IF NOT EXISTS idx_leads_resurface_after
    ON leads(resurface_after) WHERE resurface_after IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_lead_status
    ON leads(lead_status);

-- 2. Configurable cooldown durations (one row for simplicity in V1)
CREATE TABLE IF NOT EXISTS lead_status_cooldowns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key TEXT NOT NULL UNIQUE,
    days INTEGER NOT NULL CHECK (days >= 0),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

INSERT INTO lead_status_cooldowns (key, days) VALUES
    ('KNOCKED_NO_ANSWER', 7),
    ('KNOCKED_NOT_INTERESTED', 180)
ON CONFLICT (key) DO NOTHING;

COMMENT ON TABLE lead_status_cooldowns IS
    'Configurable cooldown durations (in days) for KNOCKED_* statuses. '
    'Scheduler reads this to compute resurface_after.';
