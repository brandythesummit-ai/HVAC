import apiClient from './client';

export const settingsApi = {
  // Get global Accela settings
  getAccelaSettings: async () => {
    const response = await apiClient.get('/api/settings/accela');
    return response.data;
  },

  // Update global Accela settings
  updateAccelaSettings: async (data) => {
    const response = await apiClient.put('/api/settings/accela', data);
    return response.data;
  },

  // Delete global Accela settings
  deleteAccelaSettings: async () => {
    const response = await apiClient.delete('/api/settings/accela');
    return response.data;
  },
};
