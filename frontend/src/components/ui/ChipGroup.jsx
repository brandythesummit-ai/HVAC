/**
 * Multi-select chip row. Used by FilterBar for status and tier
 * multi-selects. Value is always an array of selected option values.
 *
 * Each option: { value, label, activeClass? }. Provide `activeClass`
 * to override the default active styling (e.g. tier chips want their
 * tier color when active).
 */
const ChipGroup = ({ options, value = [], onChange, ariaLabel, className = '' }) => {
  const valueSet = new Set(value);

  const toggle = (v) => {
    if (valueSet.has(v)) {
      onChange(value.filter((x) => x !== v));
    } else {
      onChange([...value, v]);
    }
  };

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={['flex flex-wrap gap-1.5', className].join(' ')}
    >
      {options.map((opt) => {
        const active = valueSet.has(opt.value);
        const pillClass = active
          ? opt.activeClass || 'bg-primary-50 text-primary-700 border-primary-200'
          : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50';
        return (
          <button
            key={opt.value}
            type="button"
            aria-pressed={active}
            onClick={() => toggle(opt.value)}
            className={[
              'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400',
              pillClass,
            ].join(' ')}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
};

export default ChipGroup;
