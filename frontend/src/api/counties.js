import apiClient from './client';

export const countiesApi = {
  // Get all counties
  getAll: async () => {
    const response = await apiClient.get('/api/counties');
    // Backend returns {success, data: [...], error}
    // Extract just the data array
    return response.data?.data || [];
  },

  // Get single county
  getById: async (id) => {
    const response = await apiClient.get(`/api/counties/${id}`);
    return response.data;
  },

  // Create county
  create: async (data) => {
    const response = await apiClient.post('/api/counties', data);
    return response.data;
  },

  // Update county
  update: async (id, data) => {
    const response = await apiClient.put(`/api/counties/${id}`, data);
    return response.data;
  },

  // Delete county
  delete: async (id) => {
    const response = await apiClient.delete(`/api/counties/${id}`);
    return response.data;
  },

  // Test connection
  testConnection: async (id) => {
    const response = await apiClient.post(`/api/counties/${id}/test`);
    return response.data;
  },

  // Get OAuth authorization URL
  getOAuthUrl: async (id) => {
    const response = await apiClient.post(`/api/counties/${id}/oauth/authorize`);
    return response.data?.data || response.data;
  },

  // Setup county with password grant (simpler alternative to OAuth popup)
  setupWithPassword: async (id, credentials) => {
    const response = await apiClient.post(`/api/counties/${id}/oauth/password-setup`, credentials);
    return response.data;
  },

  // Get county metrics
  getMetrics: async (id) => {
    const response = await apiClient.get(`/api/counties/${id}/metrics`);
    return response.data?.data || {};
  },

  // Get pull status (for automated historical pulls)
  getPullStatus: async (id) => {
    const response = await apiClient.get(`/api/counties/${id}/pull-status`);
    return response.data?.data || {};
  },

  // Update county platform information
  updatePlatform: async (id, platformData) => {
    const response = await apiClient.patch(`/api/counties/${id}/platform`, platformData);
    return response.data?.data || response.data;
  },
};
