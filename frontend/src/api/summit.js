import apiClient from './client';

export const summitApi = {
  // Get Summit.AI configuration
  getConfig: async () => {
    const response = await apiClient.get('/api/summit/config');
    return response.data;
  },

  // Update Summit.AI configuration
  updateConfig: async (data) => {
    const response = await apiClient.put('/api/summit/config', data);
    return response.data;
  },

  // Test Summit.AI connection
  testConnection: async () => {
    const response = await apiClient.post('/api/summit/test');
    return response.data;
  },

  // Get sync status
  getSyncStatus: async () => {
    const response = await apiClient.get('/api/summit/sync-status');
    return response.data;
  },
};
