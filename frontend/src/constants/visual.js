/**
 * Centralized visual tokens for tiers and lead statuses.
 *
 * Two surfaces consume these:
 *   1. Leaflet canvas (CircleMarker pathOptions) — needs hex strings
 *   2. HTML badges (Tailwind utility classes) — needs class fragments
 *
 * Mixing the two would be a footgun (Tailwind classes don't apply to
 * Leaflet's canvas pathOptions, and hex strings can't be passed to
 * className). They're kept as distinct exports.
 */

// ---- Tier tokens ---------------------------------------------------------

// Hex fill + stroke for Leaflet CircleMarker pathOptions. White stroke
// gives every marker a halo so it survives any underlying tile color
// (the previous slate-400 cold marker disappeared over grey roads).
export const TIER_MARKER = {
  HOT:  { fill: '#e11d48', stroke: '#ffffff' }, // rose-600
  WARM: { fill: '#f59e0b', stroke: '#ffffff' }, // amber-500
  COOL: { fill: '#0ea5e9', stroke: '#ffffff' }, // sky-500
  COLD: { fill: '#475569', stroke: '#ffffff' }, // slate-600
};

// Tailwind class fragments for HTML tier badges. Dot + muted pill style
// (chosen Apr 23, 2026 — calmer than emoji, sharper than saturated fills).
export const TIER_BADGE = {
  HOT:  { dot: 'bg-rose-600',   pill: 'bg-rose-50 text-rose-700 border-rose-100',     label: 'HOT' },
  WARM: { dot: 'bg-amber-500',  pill: 'bg-amber-50 text-amber-700 border-amber-100',  label: 'WARM' },
  COOL: { dot: 'bg-sky-500',    pill: 'bg-sky-50 text-sky-700 border-sky-100',        label: 'COOL' },
  COLD: { dot: 'bg-slate-600',  pill: 'bg-slate-100 text-slate-700 border-slate-200', label: 'COLD' },
};

// Precedence ranking for stacked-marker / cluster-color decisions.
// Higher = more important. Used by ClusterMarker icon factory.
export const TIER_RANK = {
  HOT: 3,
  WARM: 2,
  COOL: 1,
  COLD: 0,
};

// ---- Status tokens -------------------------------------------------------

// Tone is an indirection so 10 statuses share 4 visual tones.
// (Avoids defining 10 colored tables — one per status — when most
// behave the same visually.)
export const STATUS_STYLES = {
  NEW:                       { label: 'New',            tone: 'slate'   },
  KNOCKED_NO_ANSWER:         { label: 'No answer',      tone: 'slate'   },
  KNOCKED_SPOKE_TO_NON_DM:   { label: 'Non-DM',         tone: 'slate'   },
  KNOCKED_WRONG_PERSON:      { label: 'Wrong person',   tone: 'slate'   },
  KNOCKED_NOT_INTERESTED:    { label: 'Not interested', tone: 'amber'   },
  INTERESTED:                { label: 'Interested',     tone: 'emerald' },
  APPOINTMENT_SET:           { label: 'Appt set',       tone: 'blue'    },
  QUOTED:                    { label: 'Quoted',         tone: 'blue'    },
  WON:                       { label: 'Won',            tone: 'emerald' },
  LOST:                      { label: 'Lost',           tone: 'slate'   },
};

// Tailwind class fragments per tone — used by Badge/StatusBadge.
export const TONE_CLASSES = {
  slate:   'bg-slate-100 text-slate-700 border-slate-200',
  amber:   'bg-amber-50 text-amber-700 border-amber-200',
  emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  blue:    'bg-blue-50 text-blue-700 border-blue-200',
  red:     'bg-red-50 text-red-700 border-red-200',
};
