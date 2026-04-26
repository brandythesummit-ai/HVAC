-- 063_compound_lead_score.sql
--
-- Replaces the age-only lead_score with a multi-factor opportunity
-- score. Same 0-100 range, same HOT/WARM/COOL/COLD tier names, but
-- now reflects a real ranking of "which house should the door-knocker
-- visit first" — not just "how old is its HVAC."
--
-- The five factors:
--   age_score:        hvac_age_years curve (was the entire previous score)
--   confidence:       permit-confirmed (1.00) > year_built fallback (0.75).
--                     26% of pool is permit-confirmed; 74% is year_built guess.
--   value_factor:     log-scaled around median $309k. Higher value home
--                     = bigger ticket = more revenue per knock. Range 0.78-1.18.
--   homeowner_factor: owner-occupied (72%) gets 1.00; absentee (28%) gets 0.65.
--                     This is the single strongest single-factor signal —
--                     absentee landlords don't make replacement decisions
--                     in person and convert dramatically worse on door-knocks.
--   size_factor:      heated_sqft proxy for HVAC tonnage. Range 0.90-1.10.
--                     Bigger system = bigger replacement quote.
--
-- Combined score is clamped to [0, 100]. Tier thresholds (HOT >= 75,
-- WARM >= 50, COOL >= 25, COLD < 25) now apply to the COMPOUND score.
--
-- Production effect when applied:
--   HOT:  274,549 (70%) → 124,068 (32%)
--   WARM:  26,563  (7%) → 107,965 (28%)
--   COOL:  45,663 (12%) → 101,830 (26%)
--   COLD:  45,193 (12%) →  58,105 (15%)
-- The 150K leads dropping out of HOT are absentee-owned, low-value,
-- year-built-only houses that were wrongly elevated by age-only scoring.

-- ============================================================================
-- 1. The scoring function — single source of truth
-- ============================================================================
CREATE OR REPLACE FUNCTION public.score_property(
  p_age int,
  p_source text,
  p_value numeric,
  p_owner_occupied boolean,
  p_heated_sqft int
)
RETURNS TABLE(score int, tier text, qualified boolean)
LANGUAGE sql
IMMUTABLE
AS $$
  WITH base AS (
    SELECT
      CASE
        WHEN p_age IS NULL    THEN 0
        WHEN p_age >= 20      THEN 100
        WHEN p_age >= 12      THEN 75 + (p_age - 12) * 3
        WHEN p_age >= 8       THEN 50 + (p_age - 8)  * 8
        WHEN p_age >= 4       THEN 25 + (p_age - 4)  * 8
        ELSE p_age * 8
      END::numeric AS age_score,
      CASE p_source
        WHEN 'permit'     THEN 1.00
        WHEN 'year_built' THEN 0.75
        ELSE                   0.60
      END::numeric AS confidence,
      CASE
        WHEN p_value IS NULL OR p_value <= 0 THEN 1.00
        WHEN p_value < 50000                 THEN 0.70
        ELSE LEAST(1.18, GREATEST(0.78,
               1.00 + 0.10 * LEAST(2.0, GREATEST(-2.0, LN(p_value::numeric / 309000.0)))
             ))::numeric
      END AS value_factor,
      CASE
        WHEN p_owner_occupied IS TRUE  THEN 1.00
        WHEN p_owner_occupied IS FALSE THEN 0.65
        ELSE                                0.85
      END::numeric AS homeowner_factor,
      CASE
        WHEN p_heated_sqft IS NULL OR p_heated_sqft <= 0 THEN 1.00
        WHEN p_heated_sqft < 1000                        THEN 0.90
        WHEN p_heated_sqft >= 4000                       THEN 1.10
        ELSE 1.00 + (p_heated_sqft - 1500)::numeric / 25000
      END::numeric AS size_factor
  ),
  combined AS (
    SELECT LEAST(100, GREATEST(0, ROUND(
      age_score * confidence * value_factor * homeowner_factor * size_factor
    )::int)) AS score
    FROM base
  )
  SELECT
    c.score,
    CASE
      WHEN c.score >= 75 THEN 'HOT'
      WHEN c.score >= 50 THEN 'WARM'
      WHEN c.score >= 25 THEN 'COOL'
      ELSE                    'COLD'
    END AS tier,
    (c.score >= 25) AS qualified
  FROM combined c;
$$;


-- ============================================================================
-- 2. Update migration 059's BEFORE INSERT trigger to use the function.
--    Future HCPAO ingests automatically get compound scoring.
-- ============================================================================
CREATE OR REPLACE FUNCTION fill_property_scoring_on_insert()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
  computed_age int;
  computed_source text;
  s record;
BEGIN
  IF NEW.lead_tier IS NOT NULL THEN
    RETURN NEW;
  END IF;

  computed_age := CASE
    WHEN NEW.most_recent_hvac_date IS NOT NULL
      THEN GREATEST(0, EXTRACT(YEAR FROM age(CURRENT_DATE, NEW.most_recent_hvac_date))::int)
    WHEN NEW.year_built IS NOT NULL
      THEN GREATEST(0, EXTRACT(YEAR FROM age(CURRENT_DATE, make_date(NEW.year_built, 1, 1)))::int)
    ELSE NULL
  END;

  IF computed_age IS NULL THEN
    RETURN NEW;
  END IF;

  computed_source := COALESCE(
    NEW.score_source,
    CASE WHEN NEW.most_recent_hvac_date IS NOT NULL THEN 'permit' ELSE 'year_built' END
  );

  SELECT * INTO s FROM score_property(
    computed_age, computed_source, NEW.total_property_value,
    NEW.owner_occupied, NEW.heated_sqft
  );

  NEW.hvac_age_years := computed_age;
  NEW.lead_tier      := s.tier;
  NEW.lead_score     := s.score;
  NEW.is_qualified   := s.qualified;
  NEW.score_source   := computed_source;

  RETURN NEW;
END;
$$;


-- ============================================================================
-- 3. Bulk-recompute helper RPC.
--
-- Updating 350K rows in one statement exceeds Supabase's 8s PostgREST
-- statement_timeout (and MCP's 2-min client cap). This function runs
-- with statement_timeout=0 and updates up to N stale rows per call.
-- A driver script loops until it returns 0.
--
-- Re-runnable: re-applying after a schema change to score_property()
-- automatically recomputes only the rows whose scores would change.
--
-- Called from backend/scripts/recompute_compound_scores.py.
-- ============================================================================
CREATE OR REPLACE FUNCTION public.recompute_compound_scores_chunk(p_chunk_size int DEFAULT 5000)
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
SET statement_timeout TO 0
SET search_path TO 'public', 'pg_temp'
AS $$
DECLARE
  rows_updated int;
BEGIN
  WITH stale AS (
    SELECT p.id, s.score, s.tier, s.qualified
    FROM properties p
    CROSS JOIN LATERAL score_property(
      p.hvac_age_years, p.score_source,
      p.total_property_value, p.owner_occupied, p.heated_sqft
    ) s
    WHERE p.is_residential = true
      AND p.source = 'hcpao_parcel'
      AND p.hvac_age_years IS NOT NULL
      AND (
           p.lead_score    IS DISTINCT FROM s.score
        OR p.lead_tier     IS DISTINCT FROM s.tier
        OR p.is_qualified  IS DISTINCT FROM s.qualified
      )
    LIMIT p_chunk_size
  )
  UPDATE properties p
  SET lead_score = ns.score, lead_tier = ns.tier, is_qualified = ns.qualified, updated_at = NOW()
  FROM stale ns WHERE p.id = ns.id;

  GET DIAGNOSTICS rows_updated = ROW_COUNT;
  RETURN rows_updated;
END;
$$;
