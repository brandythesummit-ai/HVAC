import { TIER_BADGE } from '../../constants/visual';

/**
 * Renders an optional Score line + an optional colored-dot tier pill.
 *
 * The two-line layout (Score above pill) is the existing LeadTierBadge
 * API that LeadRow.jsx:199 depends on. Don't drop it here, or the
 * /list table column will silently lose its score readout.
 */
const TierBadge = ({ tier, score }) => {
  if (!tier && (score === null || score === undefined)) {
    return <span className="text-sm text-slate-400">—</span>;
  }

  const conf = tier ? TIER_BADGE[tier] : null;

  return (
    <div className="space-y-1">
      {score !== null && score !== undefined && (
        <div className="text-sm font-bold text-slate-900">Score: {score}</div>
      )}
      {conf && (
        <span
          className={[
            'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium border',
            conf.pill,
          ].join(' ')}
        >
          <span
            aria-hidden="true"
            className={['inline-block w-1.5 h-1.5 rounded-full', conf.dot].join(' ')}
          />
          {conf.label}
        </span>
      )}
    </div>
  );
};

export default TierBadge;
