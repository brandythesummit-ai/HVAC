import { TONE_CLASSES } from '../../constants/visual';

/**
 * Base pill. Use the `tone` prop instead of writing color classes
 * directly — that keeps drift in check across StatusBadge, FilterBar
 * chip indicators, and any future surfaces that want the same palette.
 */
const Badge = ({ tone = 'slate', className = '', children }) => (
  <span
    className={[
      'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border',
      TONE_CLASSES[tone] || TONE_CLASSES.slate,
      className,
    ].join(' ')}
  >
    {children}
  </span>
);

export default Badge;
