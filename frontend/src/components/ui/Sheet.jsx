import { useEffect, useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

/**
 * Bespoke snap-point sheet, no external library.
 *
 * Mobile (<sm): anchored to bottom, supports multiple snap points
 * (e.g. [0.45, 0.88]) with drag-to-snap behavior. The drag handle on
 * top is the gesture target — dragging the body itself is intentionally
 * not supported, so internal scroll inside the sheet keeps working.
 *
 * Desktop (>=sm): if `desktopMode='modal'` (default), renders as a
 * centered modal at max(snapPoints) of viewport. If `desktopMode='sheet'`,
 * mirrors mobile drag behavior on desktop too.
 *
 * Velocity-based snap: on pointerup, the projected position is
 * `currentTop + velocity * VELOCITY_BIAS`, then we pick the closest
 * snap point. Drag-down past the lowest snap point dismisses.
 */

const VELOCITY_BIAS = 200; // px contributed per (px/ms) of recent drag velocity

const Sheet = ({
  open,
  onClose,
  side = 'bottom',
  snapPoints = [0.5, 0.9],
  initialSnap = 0,
  showCloseButton = true,
  desktopMode = 'modal',
  ariaLabel,
  className = '',
  children,
}) => {
  const sheetRef = useRef(null);
  const [snapIdx, setSnapIdx] = useState(initialSnap);
  const dragStateRef = useRef(null);
  const [dragOffset, setDragOffset] = useState(0);
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(min-width: 640px)').matches,
  );

  // Reset snap index when the sheet transitions from closed to open —
  // consecutive opens should start from the configured snap, not
  // wherever the last close happened.
  //
  // Using the "adjust state when a prop changes" pattern (setState
  // during render, guarded by previous-value comparison) instead of
  // useEffect — recommended by the React docs and avoids the
  // set-state-in-effect lint rule.
  // https://react.dev/reference/react/useState#storing-information-from-previous-renders
  const [prevOpen, setPrevOpen] = useState(open);
  if (open !== prevOpen) {
    setPrevOpen(open);
    if (open) {
      setSnapIdx(initialSnap);
      setDragOffset(0);
    }
  }

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mq = window.matchMedia('(min-width: 640px)');
    const handler = (e) => setIsDesktop(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Escape closes; lock body scroll while open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  const treatAsSheet = !isDesktop || desktopMode === 'sheet';

  const onDragStart = useCallback((e) => {
    if (!treatAsSheet) return;
    const y = e.clientY;
    dragStateRef.current = {
      startY: y,
      lastY: y,
      lastT: performance.now(),
      velocity: 0,
    };
  }, [treatAsSheet]);

  const onDragMove = useCallback((e) => {
    const ds = dragStateRef.current;
    if (!ds) return;
    const y = e.clientY;
    const now = performance.now();
    const dt = Math.max(now - ds.lastT, 1);
    ds.velocity = (y - ds.lastY) / dt; // px/ms; positive = downward
    ds.lastY = y;
    ds.lastT = now;
    const offset = y - ds.startY;
    // Allow up-drag (negative offset) up to a small overshoot — past
    // the highest snap point feels rubbery rather than fixed.
    setDragOffset(offset > 0 ? offset : Math.max(offset, -120));
  }, []);

  const onDragEnd = useCallback(() => {
    const ds = dragStateRef.current;
    if (!ds) return;
    dragStateRef.current = null;

    const vh = typeof window !== 'undefined' ? window.innerHeight : 800;
    const currentTop = vh * (1 - snapPoints[snapIdx]) + dragOffset;
    const projectedTop = currentTop + ds.velocity * VELOCITY_BIAS;

    let bestIdx = 0;
    let bestDist = Infinity;
    for (let i = 0; i < snapPoints.length; i++) {
      const targetTop = vh * (1 - snapPoints[i]);
      const d = Math.abs(targetTop - projectedTop);
      if (d < bestDist) { bestDist = d; bestIdx = i; }
    }

    // Drag-down dismissal: if projected position is well below the
    // lowest snap point with downward velocity, close instead of
    // snapping back.
    const lowestTop = vh * (1 - snapPoints[0]);
    if (projectedTop > lowestTop + vh * 0.15 && ds.velocity > 0) {
      setDragOffset(0);
      onClose?.();
      return;
    }

    setSnapIdx(bestIdx);
    setDragOffset(0);
  }, [dragOffset, snapIdx, snapPoints, onClose]);

  if (!open || typeof document === 'undefined') return null;

  const renderModal = isDesktop && desktopMode === 'modal';
  const heightPct = snapPoints[snapIdx] * 100;

  const sheetStyle = renderModal
    ? {}
    : {
        height: `${heightPct}vh`,
        transform: dragOffset !== 0 ? `translateY(${dragOffset}px)` : undefined,
        transition: dragOffset === 0
          ? 'transform 200ms ease-out, height 200ms ease-out'
          : undefined,
      };

  const sheetClasses = renderModal
    ? 'relative w-full max-w-lg mx-auto bg-white rounded-2xl shadow-xl max-h-[88vh] flex flex-col'
    : side === 'left'
      ? 'absolute top-0 bottom-0 left-0 w-[85vw] max-w-sm bg-white rounded-r-2xl shadow-sheet flex flex-col'
      : 'absolute inset-x-0 bottom-0 bg-white rounded-t-2xl shadow-sheet flex flex-col';

  const overlay = (
    <div
      className={[
        'fixed inset-0 z-sheet flex',
        renderModal ? 'items-center justify-center p-4' : 'items-end',
      ].join(' ')}
      onClick={(e) => { if (e.target === e.currentTarget) onClose?.(); }}
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
    >
      <div className="absolute inset-0 bg-slate-900/40" />
      <div ref={sheetRef} className={[sheetClasses, className].join(' ')} style={sheetStyle}>
        {treatAsSheet && side === 'bottom' && (
          <div
            className="flex justify-center pt-3 pb-1 cursor-grab active:cursor-grabbing select-none touch-none"
            onPointerDown={(e) => {
              e.currentTarget.setPointerCapture?.(e.pointerId);
              onDragStart(e);
            }}
            onPointerMove={onDragMove}
            onPointerUp={(e) => {
              e.currentTarget.releasePointerCapture?.(e.pointerId);
              onDragEnd();
            }}
            onPointerCancel={onDragEnd}
          >
            <div className="w-10 h-1 rounded-full bg-slate-300" />
          </div>
        )}
        {showCloseButton && (
          <button
            type="button"
            aria-label="Close"
            onClick={() => onClose?.()}
            className="absolute top-2 right-2 p-2 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-100 z-10"
          >
            <X className="w-5 h-5" />
          </button>
        )}
        <div className="flex-1 overflow-y-auto pb-[env(safe-area-inset-bottom)]">
          {children}
        </div>
      </div>
    </div>
  );

  return createPortal(overlay, document.body);
};

export default Sheet;
