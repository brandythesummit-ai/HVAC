import { STATUS_STYLES } from '../../constants/visual';
import Badge from './Badge';

/**
 * Looks up STATUS_STYLES[status] for a label + tone, then defers
 * to Badge for the visual rendering. The status→tone mapping lives
 * in constants/visual.js so DetailSheet, FilterBar, and any future
 * status-display surface stay aligned.
 */
const StatusBadge = ({ status, className }) => {
  const style = STATUS_STYLES[status];
  if (!style) {
    return (
      <Badge tone="slate" className={className}>
        {status || '—'}
      </Badge>
    );
  }
  return (
    <Badge tone={style.tone} className={className}>
      {style.label}
    </Badge>
  );
};

export default StatusBadge;
