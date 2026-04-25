import { forwardRef } from 'react';

/**
 * Text input with `text-base` (16px) by default — anything smaller
 * triggers iOS Safari's auto-zoom on focus, which makes the field
 * sales experience awful on a phone.
 */
const Input = forwardRef(function Input(
  { className = '', error = false, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      className={[
        'block w-full px-3 py-2 text-base rounded-lg border bg-white',
        'placeholder:text-slate-400',
        'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent',
        'disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed',
        error ? 'border-rose-400' : 'border-slate-300',
        className,
      ].join(' ')}
      {...rest}
    />
  );
});

export default Input;
