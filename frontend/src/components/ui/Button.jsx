import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

const VARIANTS = {
  primary:   'bg-primary-600 text-white hover:bg-primary-700 disabled:bg-primary-300',
  secondary: 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 disabled:bg-slate-50 disabled:text-slate-400',
  ghost:     'bg-transparent text-slate-600 hover:bg-slate-100 disabled:text-slate-300',
  danger:    'bg-rose-600 text-white hover:bg-rose-700 disabled:bg-rose-300',
  success:   'bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-emerald-300',
};

const SIZES = {
  sm: 'px-2.5 py-1.5 text-xs',
  md: 'px-3.5 py-2 text-sm',
  lg: 'px-4 py-3 text-base min-h-touch',
};

const Button = forwardRef(function Button(
  {
    variant = 'primary',
    size = 'md',
    fullWidth = false,
    loading = false,
    disabled = false,
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
      disabled={disabled || loading}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
        'active:scale-[0.98] transition-transform duration-75',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400 focus-visible:ring-offset-1',
        'disabled:cursor-not-allowed',
        fullWidth ? 'w-full' : '',
        VARIANTS[variant] || VARIANTS.primary,
        SIZES[size] || SIZES.md,
        className,
      ].join(' ')}
      {...rest}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
      {children}
    </button>
  );
});

export default Button;
