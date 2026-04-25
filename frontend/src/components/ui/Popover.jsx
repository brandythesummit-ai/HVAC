import { useEffect, useRef, useState } from 'react';

/**
 * Click-outside-aware popover anchored to a trigger. Used by
 * FilterBar's "More filters" button on desktop.
 *
 * `trigger` accepts a render function: ({ open, toggle }) => JSX,
 * which is preferred so the trigger can render its own active state.
 * A plain ReactNode is also supported (toggles on click).
 */
const Popover = ({ trigger, children, align = 'start', className = '' }) => {
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  const toggle = () => setOpen((v) => !v);

  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const alignClass =
    align === 'end' ? 'right-0'
    : align === 'center' ? 'left-1/2 -translate-x-1/2'
    : 'left-0';

  return (
    <div ref={containerRef} className="relative inline-block">
      {typeof trigger === 'function'
        ? trigger({ open, toggle })
        : (
          <span onClick={toggle} className="cursor-pointer">
            {trigger}
          </span>
        )
      }
      {open && (
        <div
          role="dialog"
          className={[
            'absolute top-full mt-1 z-filter min-w-max rounded-lg bg-white border border-slate-200 shadow-lg p-3',
            alignClass,
            className,
          ].join(' ')}
        >
          {children}
        </div>
      )}
    </div>
  );
};

export default Popover;
