import { forwardRef } from 'react';

const SIZES = {
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
  lg: 'w-11 h-11 min-w-touch min-h-touch',
};

const VARIANTS = {
  ghost:     'bg-transparent text-slate-600 hover:bg-slate-100',
  secondary: 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50',
  primary:   'bg-primary-600 text-white hover:bg-primary-700',
};

/**
 * Square icon-only button. aria-label is required so screen readers
 * have something to announce — there's no text content to fall back on.
 */
const IconButton = forwardRef(function IconButton(
  {
    'aria-label': ariaLabel,
    variant = 'ghost',
    size = 'md',
    type = 'button',
    className = '',
    children,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={ariaLabel}
      className={[
        'inline-flex items-center justify-center rounded-lg transition-colors',
        'active:scale-[0.96] transition-transform duration-75',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400 focus-visible:ring-offset-1',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        VARIANTS[variant] || VARIANTS.ghost,
        SIZES[size] || SIZES.md,
        className,
      ].join(' ')}
      {...rest}
    >
      {children}
    </button>
  );
});

export default IconButton;
