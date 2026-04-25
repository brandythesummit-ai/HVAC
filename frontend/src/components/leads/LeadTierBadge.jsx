/**
 * Backwards-compatible shim. The legacy LeadTierBadge has been
 * absorbed into the unified ui/TierBadge primitive (PR 1 of the
 * /map redesign). Re-exporting preserves LeadRow.jsx:199's prop
 * contract — `<LeadTierBadge tier={...} score={...} />` — without
 * forcing every call site to update its import path.
 *
 * Visual change: drops the emoji icon and the saturated bg-*-100
 * pill in favor of the colored-dot + muted pill style. Same
 * two-line layout (Score above pill).
 */
export { default } from '../ui/TierBadge';
