-- Migration 019: Add missing columns from code (schema drift fix)
-- These columns were added to production in commits without migration files.
-- Recovered by grepping the codebase for column references.

-- counties.token_obtained_at — used by Layer 4 of overnight-job failure prevention
ALTER TABLE counties ADD COLUMN IF NOT EXISTS token_obtained_at TIMESTAMP WITH TIME ZONE;

-- background_jobs.years_status — JSONB tracking per-year pull progress (for resume)
ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS years_status JSONB DEFAULT '{}'::jsonb;

-- background_jobs.per_year_permits — JSONB tracking per-year permit counts
ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS per_year_permits JSONB DEFAULT '{}'::jsonb;

-- background_jobs.start_year / end_year — the job's target year range
ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS start_year INTEGER;
ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS end_year INTEGER;
