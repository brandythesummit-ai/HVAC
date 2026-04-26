/**
 * PinScatterLoader — first-time map snapshot loading visual.
 *
 * Shows during the initial /api/map-snapshot fetch when no IndexedDB
 * cache exists yet. After the cache is populated once, this never
 * fires again on the same device unless the cache is cleared or the
 * schema version bumps.
 *
 * Visual: full-screen overlay with a tier-colored pin-pulse animation
 * + onboarding copy that sets expectation ("only happens once") and
 * conveys what we're doing ("caching for offline use").
 *
 * Respects `prefers-reduced-motion` — animation degrades to a static
 * pin grid for users who've opted out.
 */
import { useEffect, useState } from 'react';

const PIN_COLORS = ['#e11d48', '#f59e0b', '#e11d48', '#f59e0b', '#e11d48', '#f59e0b']; // alternating HOT/WARM

export default function PinScatterLoader({ visible, message }) {
  const [reducedMotion, setReducedMotion] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mq.matches);
    const onChange = (e) => setReducedMotion(e.matches);
    mq.addEventListener?.('change', onChange);
    return () => mq.removeEventListener?.('change', onChange);
  }, []);

  // Tick a "fake" progress that fills toward 95% over the typical
  // 5-10s download. We don't have real per-byte progress (FastAPI
  // doesn't stream the snapshot), so the bar is an expectation-setter,
  // not a true progress indicator.
  useEffect(() => {
    if (!visible) {
      setElapsedMs(0);
      return;
    }
    const start = performance.now();
    let raf;
    const tick = () => {
      setElapsedMs(performance.now() - start);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [visible]);

  if (!visible) return null;

  // Asymptotically approach 95% over ~10s. If the download finishes
  // before, the overlay just hides — no need for a frantic 0→100 jump.
  const progressPct = Math.min(95, 95 * (1 - Math.exp(-elapsedMs / 4000)));

  return (
    <div
      role="status"
      aria-live="polite"
      className="absolute inset-0 z-sheet flex items-center justify-center bg-slate-900/60 backdrop-blur-sm"
    >
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-sm mx-4 text-center">
        {/* Pulsing pin cluster */}
        <div className="flex items-center justify-center gap-1.5 mb-5 h-12">
          {PIN_COLORS.map((color, i) => (
            <span
              key={i}
              className={`block w-3 h-3 rounded-full ${reducedMotion ? '' : 'animate-bounce'}`}
              style={{
                backgroundColor: color,
                animationDelay: reducedMotion ? '0ms' : `${i * 100}ms`,
                animationDuration: '1.2s',
              }}
            />
          ))}
        </div>

        <h2 className="text-lg font-semibold text-slate-900 mb-1">
          Caching your county
        </h2>
        <p className="text-sm text-slate-500 mb-5">
          {message || 'This happens once — your map will be instant after.'}
        </p>

        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-[width] duration-200 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <div className="text-xs text-slate-400 mt-2 tabular-nums">
          {Math.round(progressPct)}%
        </div>
      </div>
    </div>
  );
}
