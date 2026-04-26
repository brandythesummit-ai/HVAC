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
 *
 * UX state machine (fixes the "progress bar didn't track" report):
 *   - hidden:     not rendered at all
 *   - opening:    `visible` just flipped true; wait OPEN_DELAY_MS so we
 *                 don't flash the loader for sub-200ms fetches
 *   - fetching:   actually shown, progress bar climbs asymptotically
 *   - completing: `visible` just flipped false; jump bar to 100%, hold
 *                 briefly, then hide. Without this, fast loads dismissed
 *                 the loader while the bar was at ~30%, looking broken.
 */
import { useEffect, useState, useRef } from 'react';

const PIN_COLORS = ['#e11d48', '#f59e0b', '#e11d48', '#f59e0b', '#e11d48', '#f59e0b']; // alternating HOT/WARM
const OPEN_DELAY_MS = 250;       // Don't render at all if the fetch finishes within this window
const COMPLETE_HOLD_MS = 350;    // Time to show the bar at 100% before unmounting
const ASYMPTOTE_TIME_MS = 1500;  // Time-constant for the progress curve (was 4000 — too slow)

export default function PinScatterLoader({ visible, message }) {
  const [reducedMotion, setReducedMotion] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  // 'hidden' | 'opening' | 'fetching' | 'completing'
  const [phase, setPhase] = useState('hidden');
  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mq.matches);
    const onChange = (e) => setReducedMotion(e.matches);
    mq.addEventListener?.('change', onChange);
    return () => mq.removeEventListener?.('change', onChange);
  }, []);

  // Drive the phase state machine off `visible` transitions
  useEffect(() => {
    if (visible) {
      // Going visible. Defer rendering by OPEN_DELAY_MS — if `visible`
      // flips back to false before the timer fires (fetch was super
      // fast), we never render at all.
      if (phaseRef.current === 'hidden') {
        const t = setTimeout(() => {
          if (phaseRef.current === 'hidden' || phaseRef.current === 'opening') {
            setPhase('fetching');
          }
        }, OPEN_DELAY_MS);
        setPhase('opening');
        return () => clearTimeout(t);
      }
    } else {
      // Going invisible. If we never made it to fetching, just hide.
      // Otherwise run completion animation.
      if (phaseRef.current === 'fetching') {
        setPhase('completing');
        const t = setTimeout(() => setPhase('hidden'), COMPLETE_HOLD_MS);
        return () => clearTimeout(t);
      }
      if (phaseRef.current !== 'hidden') {
        setPhase('hidden');
      }
    }
  }, [visible]);

  // RAF tick the elapsed time only while in fetching phase
  useEffect(() => {
    if (phase !== 'fetching') {
      if (phase === 'hidden' || phase === 'opening') setElapsedMs(0);
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
  }, [phase]);

  if (phase === 'hidden' || phase === 'opening') return null;

  // Progress: asymptotic during fetch, then snap to 100% on completion.
  // The 95% asymptote (instead of 100%) preserves the "still working"
  // affordance during fetch; jumping to exactly 100% only happens when
  // we know it's done.
  const progressPct = phase === 'completing'
    ? 100
    : Math.min(95, 95 * (1 - Math.exp(-elapsedMs / ASYMPTOTE_TIME_MS)));

  return (
    <div
      role="status"
      aria-live="polite"
      className="absolute inset-0 z-sheet flex items-center justify-center bg-slate-900/60 backdrop-blur-sm"
    >
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-sm mx-4 text-center">
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
            className="h-full bg-emerald-500 rounded-full transition-[width] duration-300 ease-out"
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
