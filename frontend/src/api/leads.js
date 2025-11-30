import apiClient from './client';

export const leadsApi = {
  // Get all leads with filters
  getAll: async (params = {}) => {
    // Filter out empty string values to avoid validation errors
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([_, value]) => value !== '' && value !== null && value !== undefined)
    );

    const response = await apiClient.get('/api/leads', { params: cleanParams });
    // Backend returns {success, data: {leads, count}, error}
    // Extract just the leads array
    return response.data?.data?.leads || [];
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
};
