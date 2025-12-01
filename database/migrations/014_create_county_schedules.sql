-- Migration 014: Create county_pull_schedules table to manage weekly incremental pulls
-- Staggers pulls across the week to avoid API overload

CREATE TABLE county_pull_schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  county_id UUID NOT NULL UNIQUE REFERENCES counties(id) ON DELETE CASCADE,

  -- When to pull (day of week: 0=Sunday, 1=Monday, etc.)
  schedule_day_of_week INTEGER NOT NULL CHECK (schedule_day_of_week >= 0 AND schedule_day_of_week <= 6),
  schedule_hour INTEGER NOT NULL DEFAULT 2 CHECK (schedule_hour >= 0 AND schedule_hour <= 23),

  -- Next scheduled pull time
  next_pull_at TIMESTAMP WITH TIME ZONE NOT NULL,

  -- Last pull tracking
  last_pull_at TIMESTAMP WITH TIME ZONE,
  last_pull_status TEXT CHECK (last_pull_status IN ('success', 'failed', 'pending')),

  -- Auto-pull settings
  auto_pull_enabled BOOLEAN DEFAULT TRUE,
  incremental_pull_enabled BOOLEAN DEFAULT TRUE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for finding counties due for pull
CREATE INDEX idx_county_schedules_next_pull ON county_pull_schedules(next_pull_at) WHERE auto_pull_enabled = TRUE;

-- Index for load balancing across days
CREATE INDEX idx_county_schedules_day ON county_pull_schedules(schedule_day_of_week);
