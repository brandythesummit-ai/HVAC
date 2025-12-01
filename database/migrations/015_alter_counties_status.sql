-- Migration 015: Add county status columns for tracking pull completion and stats
-- Provides quick access to pull status without joining to background_jobs table

ALTER TABLE counties
ADD COLUMN initial_pull_completed BOOLEAN DEFAULT FALSE,
ADD COLUMN initial_pull_job_id UUID REFERENCES background_jobs(id) ON DELETE SET NULL,
ADD COLUMN last_incremental_pull_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN total_permits_pulled INTEGER DEFAULT 0,
ADD COLUMN total_leads_created INTEGER DEFAULT 0;

-- Index for finding counties that haven't completed initial pull
CREATE INDEX idx_counties_initial_pull ON counties(initial_pull_completed);
