import { forwardRef } from 'react';
import { ChevronDown } from 'lucide-react';

/**
 * Native <select> wrapped with a custom chevron + 16px text.
 * Native is intentional — it gives mobile its OS-native picker
 * (drum roll on iOS, dropdown on Android) which is far better
 * than any custom JS dropdown for one-handed field-sales use.
 */
const Select = forwardRef(function Select(
  { className = '', children, ...rest },
  ref,
) {
  return (
    <div className="relative">
      <select
        ref={ref}
        className={[
          'block w-full appearance-none px-3 py-2 pr-9 text-base rounded-lg border border-slate-300 bg-white',
          'focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent',
          'disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed',
          className,
        ].join(' ')}
        {...rest}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden="true"
        className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none"
      />
    </div>
  );
});

export default Select;
