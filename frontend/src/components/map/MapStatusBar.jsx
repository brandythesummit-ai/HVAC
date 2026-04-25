import { Plus } from 'lucide-react';

/**
 * Multi-state hint chip rendered over the map's bottom-left corner.
 *
 * Replaces the single-text chip at MapPage.jsx:249-251 with a
 * structured priority-based renderer so that "searching", "too broad",
 * "no match", "below min zoom", "truncated", and "pinned" each get
 * their own visual treatment instead of being concatenated into one
 * prose line.
 *
 * State priority (first match wins):
 *   searching > tooBroad > noMatch > belowMinZoom > truncated > pinned
 *
 * Truncation: the /api/map-pins response only carries a boolean
 * `truncated` flag (no overage count — see map_pins.py:79), so the
 * message reads "more in this area" rather than citing a number.
 *
 * Mobile (variant="mobile"): repositions to clear the BottomNav (bottom-20)
 * — the BottomNav primitive lands in PR 3.
 */

const TONES = {
  slate:  'bg-white/95 text-slate-700 border-slate-200',
  amber:  'bg-amber-50/95 text-amber-800 border-amber-200',
};

const baseClasses = 'rounded-lg border px-3 py-1.5 text-xs shadow-md font-medium';

const MapStatusBar = ({
  searching = false,
  tooBroad = false,
  noMatch = false,
  belowMinZoom = false,
  truncated = false,
  searchQuery = '',
  searchCount = 0,
  pinnedCount = 0,
  onZoomIn,
  variant = 'desktop',
}) => {
  const positionClass = variant === 'mobile' ? 'absolute bottom-20 left-3 z-10' : 'absolute bottom-3 left-3 z-10';

  if (searching) {
    return (
      <div className={`${positionClass} ${baseClasses} ${TONES.slate}`} role="status" aria-live="polite">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-2 h-2 rounded-full bg-slate-400 animate-pulse" aria-hidden="true" />
          Searching addresses…
        </span>
      </div>
    );
  }

  if (tooBroad) {
    return (
      <div className={`${positionClass} ${baseClasses} ${TONES.amber}`} role="status">
        <span>
          <span className="font-bold">{searchCount.toLocaleString()}+</span> matches for
          {' '}<span className="italic">"{searchQuery}"</span> — refine
        </span>
      </div>
    );
  }

  if (noMatch) {
    return (
      <div className={`${positionClass} ${baseClasses} ${TONES.slate}`} role="status">
        No matches for <span className="italic">"{searchQuery}"</span>
      </div>
    );
  }

  if (belowMinZoom) {
    return (
      <div className={`${positionClass} ${baseClasses} ${TONES.slate}`} role="status">
        <span className="inline-flex items-center gap-2">
          Zoom in to load pins
          {onZoomIn && (
            <button
              type="button"
              aria-label="Zoom in"
              onClick={onZoomIn}
              className="inline-flex items-center justify-center w-5 h-5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700"
            >
              <Plus className="w-3 h-3" />
            </button>
          )}
        </span>
      </div>
    );
  }

  if (truncated) {
    return (
      <div className={`${positionClass} ${baseClasses} ${TONES.amber}`} role="status">
        <span className="font-bold">{pinnedCount.toLocaleString()}</span> pinned · more in this area — zoom in
      </div>
    );
  }

  return (
    <div className={`${positionClass} ${baseClasses} ${TONES.slate}`} role="status">
      <span className="font-bold">{pinnedCount.toLocaleString()}</span> pinned
    </div>
  );
};

export default MapStatusBar;
