import apiClient from './client';

// FilterBar uses its own param names for URL-sync readability. The backend
// at /api/leads uses snake_case names from before the post-pivot rebuild.
// Translate here so neither side has to change its naming convention.
// Arrays get comma-joined — the backend splits on commas for list filters.
const FILTER_KEY_MAP = {
  tier: 'lead_tier',
  status: 'status',
  minAge: 'min_hvac_age',
  maxAge: 'max_hvac_age',
  valueMin: 'min_property_value',
  valueMax: 'max_property_value',
  dateFrom: 'date_from',
  dateTo: 'date_to',
  zip: 'zip',
  ownerOccupied: 'owner_occupied',
  permitType: 'permit_type',
  search: 'search',
};

function toBackendParams(params = {}) {
  const out = {};
  for (const [k, v] of Object.entries(params)) {
    if (v === '' || v == null) continue;
    const backendKey = FILTER_KEY_MAP[k] || k;
    out[backendKey] = Array.isArray(v) ? v.join(',') : v;
  }
  return out;
}

export const leadsApi = {
  // Get all leads with filters and pagination metadata
  getAll: async (params = {}) => {
    const cleanParams = toBackendParams(params);
    const response = await apiClient.get('/api/leads', { params: cleanParams });
    // Backend returns {success, data: {leads, count, total, limit, offset}, error}
    // Return full data object with pagination metadata
    return response.data?.data || { leads: [], count: 0, total: 0, limit: 50, offset: 0 };
  },

  // Create leads from permits
  createFromPermits: async (permitIds) => {
    const response = await apiClient.post('/api/leads/create-from-permits', {
      permit_ids: permitIds,
    });
    return response.data;
  },

  // Update lead notes
  updateNotes: async (id, notes) => {
    const response = await apiClient.put(`/api/leads/${id}/notes`, { notes });
    return response.data;
  },

  // Sync leads to Summit.AI
  syncToSummit: async (leadIds = []) => {
    const response = await apiClient.post('/api/leads/sync-to-summit', {
      lead_ids: leadIds,
    });
    return response.data;
  },

  // Delete a lead by ID
  delete: async (id) => {
    const response = await apiClient.delete(`/api/leads/${id}`);
    return response.data;
  },

  // M19: transition lead status via the state machine endpoint.
  // The backend computes cooldown + GHL-push flag from the transition.
  updateStatus: async (id, { newStatus, note }) => {
    const response = await apiClient.patch(`/api/leads/${id}/status`, {
      new_status: newStatus,
      note,
    });
    return response.data;
  },
};
