-- Migration 020: Properties pipeline intelligence columns (schema drift fix)
-- More columns the production code expects, added in prod without migrations.

ALTER TABLE properties ADD COLUMN IF NOT EXISTS contact_completeness TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS affluence_tier TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS recommended_pipeline TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS pipeline_confidence TEXT;

CREATE INDEX IF NOT EXISTS idx_properties_affluence_tier ON properties(affluence_tier);
CREATE INDEX IF NOT EXISTS idx_properties_recommended_pipeline ON properties(recommended_pipeline);
