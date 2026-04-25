/**
 * Pill-shaped horizontal toggle. Used by the desktop ViewToggle
 * (Map / List / Plan) once Layout.jsx hosts it in the top header.
 *
 * Each option: { value, label, icon? }. The active option gets a
 * white card behind it; inactive options are flat slate text.
 */
const SegmentedControl = ({ options, value, onChange, ariaLabel, className = '' }) => (
  <div
    role="tablist"
    aria-label={ariaLabel}
    className={['inline-flex items-center p-1 bg-slate-100 rounded-lg', className].join(' ')}
  >
    {options.map((opt) => {
      const active = opt.value === value;
      const Icon = opt.icon;
      return (
        <button
          key={opt.value}
          role="tab"
          aria-selected={active}
          type="button"
          onClick={() => onChange(opt.value)}
          className={[
            'inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400',
            active
              ? 'bg-white text-slate-900 shadow-sm'
              : 'bg-transparent text-slate-500 hover:text-slate-700',
          ].join(' ')}
        >
          {Icon && <Icon aria-hidden="true" className="w-4 h-4" />}
          {opt.label}
        </button>
      );
    })}
  </div>
);

export default SegmentedControl;
