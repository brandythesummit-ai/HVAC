import apiClient from './client';

export const healthApi = {
  // Get comprehensive health status
  getHealth: async () => {
    const response = await apiClient.get('/api/health');
    return response.data;
  },
};
