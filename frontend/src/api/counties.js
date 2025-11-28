import apiClient from './client';

export const countiesApi = {
  // Get all counties
  getAll: async () => {
    const response = await apiClient.get('/api/counties');
    return response.data;
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
};
