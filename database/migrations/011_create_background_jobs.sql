-- Migration 011: Create background_jobs table for job queue
-- Purpose: Track long-running permit pulls with progress metrics (DB-based queue, no Celery/Redis needed)

CREATE TABLE IF NOT EXISTS background_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_id UUID NOT NULL REFERENCES counties(id) ON DELETE CASCADE,

    -- Job Configuration
    job_type TEXT NOT NULL,  -- 'initial_pull' (30 year historical), 'incremental_pull' (daily new permits)
    status TEXT DEFAULT 'pending' NOT NULL,  -- 'pending', 'running', 'completed', 'failed', 'cancelled'

    -- Job Parameters (stored as JSONB for flexibility)
    parameters JSONB,  -- { years: 30, permit_type: "Building/Residential/Trade/Mechanical", date_from, date_to, limit, etc. }

    -- Progress Tracking
    permits_pulled INTEGER DEFAULT 0,
    permits_saved INTEGER DEFAULT 0,
    permits_failed INTEGER DEFAULT 0,
    properties_created INTEGER DEFAULT 0,
    properties_updated INTEGER DEFAULT 0,
    leads_created INTEGER DEFAULT 0,
    leads_updated INTEGER DEFAULT 0,
    current_year INTEGER,  -- Track which year we're currently pulling (e.g., 2015 when pulling 1995-2025)
    current_batch INTEGER DEFAULT 0,  -- Track batch number within current year

    -- Performance Metrics
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    elapsed_seconds INTEGER,
    estimated_completion_at TIMESTAMP WITH TIME ZONE,
    permits_per_second NUMERIC(10, 2),
    progress_percent INTEGER DEFAULT 0,  -- 0-100

    -- Error Handling
    error_message TEXT,
    error_details JSONB,  -- Stack trace, failed permit IDs, etc.
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- Constraints
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    CHECK (job_type IN ('initial_pull', 'incremental_pull', 'property_aggregation')),
    CHECK (progress_percent >= 0 AND progress_percent <= 100)
);

-- Indexes for performance
CREATE INDEX idx_background_jobs_county_id ON background_jobs(county_id);
CREATE INDEX idx_background_jobs_status ON background_jobs(status);
CREATE INDEX idx_background_jobs_job_type ON background_jobs(job_type);
CREATE INDEX idx_background_jobs_created_at ON background_jobs(created_at DESC);
CREATE INDEX idx_background_jobs_updated_at ON background_jobs(updated_at DESC);

-- Composite indexes for common queries
CREATE INDEX idx_background_jobs_county_status ON background_jobs(county_id, status);
CREATE INDEX idx_background_jobs_type_status ON background_jobs(job_type, status);

-- Partial index for active jobs (polling optimization)
CREATE INDEX idx_background_jobs_pending ON background_jobs(created_at) WHERE status = 'pending';
CREATE INDEX idx_background_jobs_running ON background_jobs(started_at) WHERE status = 'running';

-- Comments for documentation
COMMENT ON TABLE background_jobs IS 'Background job tracking for long-running permit pulls and property aggregations. DB-based queue (no external dependencies).';
COMMENT ON COLUMN background_jobs.job_type IS 'Job type: initial_pull (30 year historical load), incremental_pull (daily new permits), property_aggregation (rebuild property records)';
COMMENT ON COLUMN background_jobs.status IS 'Job status: pending (queued), running (in progress), completed (success), failed (error), cancelled (user stopped)';
COMMENT ON COLUMN background_jobs.parameters IS 'Job-specific parameters as JSON. Example: {"years": 30, "permit_type": "Building/Residential/Trade/Mechanical"}';
COMMENT ON COLUMN background_jobs.current_year IS 'Year currently being processed (for 30-year pull: 2025 → 1995). Used to calculate progress.';
COMMENT ON COLUMN background_jobs.estimated_completion_at IS 'Estimated completion time based on current processing rate (permits_per_second)';
COMMENT ON COLUMN background_jobs.progress_percent IS 'Overall job progress as percentage (0-100). Calculated as (current_year - start_year) / total_years * 100';
COMMENT ON COLUMN background_jobs.retry_count IS 'Number of retry attempts after failure. Jobs auto-retry up to max_retries times.';
