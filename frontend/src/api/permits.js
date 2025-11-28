import apiClient from './client';

export const permitsApi = {
  // Pull permits from Accela
  pullPermits: async (countyId, params) => {
    const response = await apiClient.post(`/api/counties/${countyId}/pull-permits`, params);
    return response.data;
  },

  // Get all permits with filters
  getAll: async (params = {}) => {
    const response = await apiClient.get('/api/permits', { params });
    return response.data;
  },

  // Get single permit
  getById: async (id) => {
    const response = await apiClient.get(`/api/permits/${id}`);
    return response.data;
  },
};
