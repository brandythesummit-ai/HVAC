import apiClient from './client';

export const jobsApi = {
  // Create a new background job for initial 30-year pull
  createInitialPull: async (countyId, years = 30) => {
    const response = await apiClient.post(`/api/background-jobs/counties/${countyId}/jobs`, {
      job_type: 'initial_pull',
      years
    });
    return response.data;
  },

  // Get job status (for polling)
  getJob: async (jobId) => {
    const response = await apiClient.get(`/api/background-jobs/jobs/${jobId}`);
    return response.data;
  },

  // Cancel a running job
  cancelJob: async (jobId) => {
    const response = await apiClient.post(`/api/background-jobs/jobs/${jobId}/cancel`);
    return response.data;
  },

  // Delete a completed/failed job
  deleteJob: async (jobId) => {
    const response = await apiClient.delete(`/api/background-jobs/jobs/${jobId}`);
    return response.data;
  },

  // List all jobs for a county
  listJobs: async (countyId) => {
    const response = await apiClient.get(`/api/background-jobs/counties/${countyId}/jobs`);
    return response.data;
  },
};

export default jobsApi;
