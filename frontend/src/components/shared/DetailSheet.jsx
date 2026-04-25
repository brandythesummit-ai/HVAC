/**
 * DetailSheet — the interactive core of the post-knock workflow.
 *
 * Layout: snap-point bottom sheet on mobile (45% peek → drag-up to 88%
 * full detail), centered modal on desktop. Built on the bespoke ui/Sheet
 * primitive instead of the previous in-line modal — same UX, less
 * duplicated chrome.
 *
 * Mounted once at App.jsx root; listens for 'open-lead-detail' events
 * dispatched from MapPage pins (event detail: `{ propertyId }`) and
 * ListPage rows (event detail: `{ id }`).
 *
 * Stages on mobile (snap points 0.45 / 0.88):
 *   Stage 1 (peek): identity, badges, knock-outcome action grid.
 *     Map stays visible behind so the door-knocker keeps spatial
 *     context for the next house.
 *   Stage 2 (expand): notes, full LeadDetailView (all Accela raw_data
 *     per design doc §2 "ALL data retrieved from Accela SHALL be visible").
 *
 * Status transitions go through the lead-status machine on the backend
 * (cooldowns + GHL push are computed server-side). Successful transitions
 * trigger navigator.vibrate(10) for haptic confirmation on Android
 * (no-op on iOS, which doesn't expose the Vibration API).
 */
import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';

import { useUpdateLeadStatus } from '../../hooks/useLeads';
import apiClient from '../../api/client';
import Sheet from '../ui/Sheet';
import TierBadge from '../ui/TierBadge';
import StatusBadge from '../ui/StatusBadge';
import LeadDetailView from '../leads/LeadDetailView';

// Action-intent colors (kept hardcoded — see advisor correction #9 in
// the plan). These describe the action being taken, not the resulting
// state, so they don't share a palette with the StatusBadge tones.
const KNOCK_ACTIONS = [
  { label: 'No answer',         status: 'KNOCKED_NO_ANSWER',       color: 'bg-slate-600 hover:bg-slate-700' },
  { label: 'Not decision-maker',status: 'KNOCKED_SPOKE_TO_NON_DM', color: 'bg-slate-600 hover:bg-slate-700' },
  { label: 'Wrong person',      status: 'KNOCKED_WRONG_PERSON',    color: 'bg-slate-700 hover:bg-slate-800' },
  { label: 'Not interested',    status: 'KNOCKED_NOT_INTERESTED',  color: 'bg-amber-600 hover:bg-amber-700' },
  { label: 'Interested!',       status: 'INTERESTED',              color: 'bg-emerald-600 hover:bg-emerald-700', primary: true },
];

const POST_INTERESTED_ACTIONS = [
  { label: 'Appointment set', status: 'APPOINTMENT_SET', color: 'bg-blue-600 hover:bg-blue-700' },
  { label: 'Quoted',          status: 'QUOTED',          color: 'bg-blue-700 hover:bg-blue-800' },
  { label: 'Won',             status: 'WON',             color: 'bg-emerald-700 hover:bg-emerald-800' },
  { label: 'Lost',            status: 'LOST',            color: 'bg-slate-500 hover:bg-slate-600' },
];

export default function DetailSheet() {
  const [openKey, setOpenKey] = useState(null);
  const [lead, setLead] = useState(null);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const updateStatus = useUpdateLeadStatus();

  // Listen for open-lead-detail events. propertyId comes from MapPage
  // pin clicks (lean map-pins payload), id comes from ListPage rows
  // (full lead record).
  useEffect(() => {
    const handler = (e) => {
      const d = e.detail || {};
      if (d.propertyId) {
        setOpenKey({ by: 'property', id: d.propertyId });
      } else if (d.id) {
        setOpenKey({ by: 'lead', id: d.id });
      } else {
        setOpenKey(null);
      }
      setNote('');
    };
    window.addEventListener('open-lead-detail', handler);
    return () => window.removeEventListener('open-lead-detail', handler);
  }, []);

  // Reset lead state on every openKey transition. Using the
  // "adjust state when prop changes" pattern (setState during render,
  // guarded by previous-value comparison) instead of useEffect to
  // avoid the react-hooks/set-state-in-effect rule.
  // See: https://react.dev/reference/react/useState#storing-information-from-previous-renders
  const [renderedOpenKey, setRenderedOpenKey] = useState(openKey);
  if (openKey !== renderedOpenKey) {
    setRenderedOpenKey(openKey);
    setLead(null);
  }

  // When a lead is selected, fetch its full detail. The reset of
  // `lead` to null on transitions happens above during render; this
  // effect only handles the "open" side of the transition.
  useEffect(() => {
    if (!openKey) return;
    let cancelled = false;
    setLoading(true);
    const url = openKey.by === 'property'
      ? `/api/leads/by-property/${openKey.id}`
      : `/api/leads/${openKey.id}`;
    apiClient
      .get(url)
      .then((res) => {
        if (!cancelled) setLead(res.data?.data || res.data);
      })
      .catch((err) => {
        if (!cancelled) toast.error(`Failed to load lead: ${err.message}`);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [openKey]);

  const close = () => setOpenKey(null);

  // Which transition buttons to show depends on current status.
  const availableActions = useMemo(() => {
    if (!lead) return [];
    const s = lead.lead_status;
    if (!s || s === 'NEW' || s.startsWith('KNOCKED_')) return KNOCK_ACTIONS;
    return POST_INTERESTED_ACTIONS;
  }, [lead]);

  const onTransition = async (newStatus) => {
    if (!lead) return;
    try {
      await updateStatus.mutateAsync({
        id: lead.id,
        newStatus,
        note: note.trim() || undefined,
      });
      // Haptic confirmation on Android (iOS Safari ignores; no-op).
      navigator.vibrate?.(10);
      toast.success(`Status → ${newStatus.replace(/_/g, ' ')}`);
      close();
    } catch (err) {
      toast.error(err.response?.data?.error || err.message || 'Failed to update status');
    }
  };

  const isOpen = openKey !== null;

  return (
    <Sheet
      open={isOpen}
      onClose={close}
      side="bottom"
      snapPoints={[0.45, 0.88]}
      initialSnap={0}
      ariaLabel="Lead detail"
      desktopMode="modal"
      showCloseButton
    >
      <div className="px-4 pb-4">
        {loading && <div className="py-6 text-slate-500">Loading…</div>}

        {!loading && lead && (
          <>
            {/* Stage 1 content — visible at the 45% peek snap.
                Identity + badges + action grid come first so the
                core workflow is reachable without dragging up. */}
            <div className="space-y-3">
              <div className="pr-8">
                <div className="text-xs text-slate-500 uppercase tracking-wide">Property</div>
                <div className="font-semibold text-base">
                  {lead.normalized_address || lead.property_address || '(no address)'}
                </div>
                {(lead.city || lead.zip_code) && (
                  <div className="text-xs text-slate-500">
                    {[lead.city, lead.state, lead.zip_code].filter(Boolean).join(', ')}
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">Tier</div>
                  <div className="mt-0.5">
                    {lead.lead_tier
                      ? <TierBadge tier={lead.lead_tier} />
                      : <span className="text-slate-400">—</span>}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">Status</div>
                  <div className="mt-0.5">
                    <StatusBadge status={lead.lead_status || 'NEW'} />
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">HVAC age</div>
                  <div className="font-medium">{lead.hvac_age_years ?? '—'} yrs</div>
                  {lead.properties?.score_source === 'permit' && (
                    <div className="text-[11px] text-emerald-700 mt-0.5">✓ Confirmed via permit</div>
                  )}
                  {lead.properties?.score_source === 'year_built' && (
                    <div className="text-[11px] text-amber-700 mt-0.5">ⓘ Estimated from build year</div>
                  )}
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">Score</div>
                  <div className="font-medium">{lead.lead_score ?? 0}</div>
                </div>
              </div>

              {lead.owner_name && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">Owner</div>
                  <div className="text-sm">{lead.owner_name}</div>
                  {lead.owner_phone && (
                    <a href={`tel:${lead.owner_phone}`} className="text-sm text-primary-600 hover:underline">
                      {lead.owner_phone}
                    </a>
                  )}
                  {lead.owner_email && (
                    <a href={`mailto:${lead.owner_email}`} className="text-sm text-primary-600 hover:underline block">
                      {lead.owner_email}
                    </a>
                  )}
                </div>
              )}

              {lead.resurface_after && (
                <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-2">
                  Resurfaces on: {new Date(lead.resurface_after).toLocaleDateString()}
                </div>
              )}

              {/* Action buttons. Grid-cols-2 with the primary "Interested!"
                  spanning both columns at the bottom for thumb-reach. All
                  buttons are min-h-touch (44px) per the mobile affordance
                  rules in the plan. */}
              <div className="grid grid-cols-2 gap-2 pt-2">
                {availableActions.filter((a) => !a.primary).map((action) => (
                  <button
                    key={action.status}
                    type="button"
                    onClick={() => onTransition(action.status)}
                    disabled={updateStatus.isPending}
                    className={
                      `min-h-touch py-2 rounded-lg text-white text-sm font-medium transition-colors ${action.color} ` +
                      'active:scale-[0.98] transition-transform duration-75 ' +
                      'disabled:opacity-50 disabled:cursor-not-allowed ' +
                      'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400'
                    }
                  >
                    {action.label}
                  </button>
                ))}
                {availableActions.filter((a) => a.primary).map((action) => (
                  <button
                    key={action.status}
                    type="button"
                    onClick={() => onTransition(action.status)}
                    disabled={updateStatus.isPending}
                    className={
                      `col-span-2 min-h-touch py-3 rounded-lg text-white text-base font-semibold transition-colors ${action.color} ` +
                      'active:scale-[0.98] transition-transform duration-75 ' +
                      'disabled:opacity-50 disabled:cursor-not-allowed ' +
                      'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400'
                    }
                  >
                    {action.label}
                  </button>
                ))}
              </div>

              {/* Notes input — sits below action buttons because most
                  knock outcomes don't need a note. Type-tab order:
                  user can still tap the textarea before tapping an
                  action button if they want to add context. */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Note (optional)
                </label>
                <textarea
                  rows={2}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="e.g., Was at work — try evening"
                  className="w-full px-3 py-2 text-base border border-slate-200 rounded-lg focus:border-primary-500 outline-none"
                />
              </div>
            </div>

            {/* Stage 2 content — full Accela / parcel detail. Hidden
                behind the user dragging the sheet up to the 88% snap.
                LeadDetailView renders all raw_data fields per the
                design doc's "ALL data retrieved from Accela SHALL be
                visible" requirement. */}
            <div className="mt-4 pt-4 border-t border-slate-200">
              <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">
                Full detail
              </div>
              <LeadDetailView lead={lead} />
            </div>
          </>
        )}
      </div>
    </Sheet>
  );
}
