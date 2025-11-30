import apiClient from './client';

export const propertiesApi = {
  // Get a specific property
  getProperty: async (propertyId) => {
    const response = await apiClient.get(`/api/properties/${propertyId}`);
    return response.data;
  },

  // Get all permits for a property
  getPropertyPermits: async (propertyId) => {
    const response = await apiClient.get(`/api/properties/${propertyId}/permits`);
    return response.data;
  },

  // List properties for a county
  listProperties: async (countyId, filters = {}) => {
    const params = new URLSearchParams();

    if (filters.lead_tier) params.append('lead_tier', filters.lead_tier);
    if (filters.is_qualified !== undefined) params.append('is_qualified', filters.is_qualified);
    if (filters.min_score) params.append('min_score', filters.min_score);
    if (filters.max_score) params.append('max_score', filters.max_score);
    if (filters.city) params.append('city', filters.city);
    if (filters.page) params.append('page', filters.page);
    if (filters.page_size) params.append('page_size', filters.page_size);

    const response = await apiClient.get(`/api/properties/counties/${countyId}/properties?${params.toString()}`);
    return response.data;
  },

  // Get property statistics for a county
  getPropertyStats: async (countyId) => {
    const response = await apiClient.get(`/api/properties/counties/${countyId}/properties/stats`);
    return response.data;
  },
};

export default propertiesApi;
