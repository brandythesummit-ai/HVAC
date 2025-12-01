-- Migration 013: Create pull_history table to track which date ranges have been pulled
-- This prevents redundant API calls by recording what data has already been fetched

CREATE TABLE pull_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  county_id UUID NOT NULL REFERENCES counties(id) ON DELETE CASCADE,
  pull_type TEXT NOT NULL CHECK (pull_type IN ('initial', 'incremental')),
  date_from DATE NOT NULL,
  date_to DATE NOT NULL,
  permits_pulled INTEGER DEFAULT 0,
  permits_saved INTEGER DEFAULT 0,
  leads_created INTEGER DEFAULT 0,
  job_id UUID REFERENCES background_jobs(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_pull_history_county ON pull_history(county_id);
CREATE INDEX idx_pull_history_dates ON pull_history(date_from, date_to);
CREATE INDEX idx_pull_history_type ON pull_history(county_id, pull_type);
