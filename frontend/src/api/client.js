import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120 seconds (2 minutes) - increased for client-side filtering
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth tokens in the future
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token here if needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = error.response?.data?.detail || error.message || 'An error occurred';

    // If detail is an array (FastAPI validation errors), extract messages
    if (Array.isArray(message)) {
      message = message.map(err => err.msg || JSON.stringify(err)).join(', ');
    }

    // If detail is an object, stringify it
    if (typeof message === 'object' && message !== null) {
      message = JSON.stringify(message);
    }

    return Promise.reject(new Error(message));
  }
);

export default apiClient;
