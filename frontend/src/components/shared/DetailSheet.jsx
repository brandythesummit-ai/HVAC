/**
 * DetailSheet — the interactive core of the post-knock workflow.
 *
 * Layout: bottom-sheet on mobile (slides up from bottom), centered
 * modal on desktop. Renders when 'open-lead-detail' event fires
 * (MapPage pin click, ListPage row click).
 *
 * What it shows:
 *   - All permit fields pulled from raw_data (design doc §2
 *     "ALL data retrieved from Accela SHALL be visible")
 *   - Current lead_status + tier badge
 *   - Big status-transition buttons for the 5 post-knock outcomes
 *   - Notes input (goes into status_note when a transition happens)
 *   - Push-to-GHL button (only visible for INTERESTED status)
 *
 * Status transitions use the lead_status_machine via the backend —
 * cooldowns and GHL-push flags are computed server-side.
 */
import { useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import toast from 'react-hot-toast';

import { useUpdateLeadStatus } from '../../hooks/useLeads';
import apiClient from '../../api/client';

const KNOCK_ACTIONS = [
  { label: 'No answer', status: 'KNOCKED_NO_ANSWER', color: 'bg-slate-600' },
  { label: 'Not decision-maker', status: 'KNOCKED_SPOKE_TO_NON_DM', color: 'bg-slate-600' },
  { label: 'Wrong person', status: 'KNOCKED_WRONG_PERSON', color: 'bg-slate-700' },
  { label: 'Not interested', status: 'KNOCKED_NOT_INTERESTED', color: 'bg-amber-600' },
  { label: 'Interested!', status: 'INTERESTED', color: 'bg-emerald-600' },
];

const POST_INTERESTED_ACTIONS = [
  { label: 'Appointment set', status: 'APPOINTMENT_SET', color: 'bg-blue-600' },
  { label: 'Quoted', status: 'QUOTED', color: 'bg-blue-700' },
  { label: 'Won', status: 'WON', color: 'bg-emerald-700' },
  { label: 'Lost', status: 'LOST', color: 'bg-slate-500' },
];

export default function DetailSheet() {
  // openKey: either { by: 'lead', id } (ListPage) or { by: 'property', id } (MapPage).
  // Pins on the map carry property_id (they're rendered from the lean map-pins RPC,
  // not from leads), so we resolve via /api/leads/by-property/:id for that path.
  const [openKey, setOpenKey] = useState(null);
  const [lead, setLead] = useState(null);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const updateStatus = useUpdateLeadStatus();

  // Listen for open-lead-detail events from MapPage / ListPage
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

  // When a lead is selected, fetch its full detail
  useEffect(() => {
    if (!openKey) {
      setLead(null);
      return;
    }
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
    return () => {
      cancelled = true;
    };
  }, [openKey]);

  const close = () => setOpenKey(null);

  // Which transition buttons to show depends on current status
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
      toast.success(`Status → ${newStatus.replace(/_/g, ' ')}`);
      close();
    } catch (err) {
      toast.error(err.response?.data?.error || err.message || 'Failed to update status');
    }
  };

  if (!openKey) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex items-end sm:items-center justify-center"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={close}
      />

      {/* Sheet */}
      <div className="relative bg-white w-full sm:max-w-lg max-h-[85vh] sm:rounded-2xl rounded-t-2xl shadow-xl overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
          <h2 className="font-semibold">Lead detail</h2>
          <button
            onClick={close}
            aria-label="Close"
            className="text-slate-500 hover:text-slate-800"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading && <div className="text-slate-500">Loading…</div>}
          {!loading && lead && (
            <>
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wide">Property</div>
                <div className="font-medium">{lead.property_address || '(no address)'}</div>
              </div>
              {lead.owner_name && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">Owner</div>
                  <div>{lead.owner_name}</div>
                  {lead.owner_phone && <div className="text-sm">{lead.owner_phone}</div>}
                  {lead.owner_email && <div className="text-sm">{lead.owner_email}</div>}
                </div>
              )}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">HVAC age</div>
                  <div>{lead.hvac_age_years ?? '—'} yrs</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">Score</div>
                  <div>{lead.lead_score ?? 0}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">Tier</div>
                  <div>{lead.lead_tier || '—'}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">Status</div>
                  <div>{(lead.lead_status || 'NEW').replace(/_/g, ' ')}</div>
                </div>
              </div>
              {lead.most_recent_hvac_date && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wide">
                    Most recent HVAC permit
                  </div>
                  <div className="text-sm">{lead.most_recent_hvac_date}</div>
                </div>
              )}
              {lead.total_hvac_permits != null && (
                <div className="text-sm text-slate-600">
                  {lead.total_hvac_permits} HVAC permit(s) on record
                </div>
              )}
              {lead.resurface_after && (
                <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-2">
                  Resurfaces on: {new Date(lead.resurface_after).toLocaleDateString()}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Note (optional)
                </label>
                <textarea
                  rows={2}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="e.g., Was at work — try evening"
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:border-blue-500 outline-none text-sm"
                />
              </div>
            </>
          )}
        </div>

        {!loading && lead && (
          <div className="border-t border-slate-200 p-3 space-y-2">
            <div className="grid grid-cols-2 gap-2">
              {availableActions.map((action) => (
                <button
                  key={action.status}
                  onClick={() => onTransition(action.status)}
                  disabled={updateStatus.isPending}
                  className={
                    `py-2 rounded-lg text-white text-sm font-medium ${action.color} ` +
                    'disabled:opacity-50'
                  }
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
