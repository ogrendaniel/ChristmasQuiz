// API configuration
// Backend ngrok URL - update this when ngrok URLs change
export const API_URL = 'http://13.53.35.42';

// Helper function for API calls that bypasses ngrok warning
export const fetchAPI = (url, options = {}) => {
  return fetch(url, {
    ...options,
    headers: {
      'ngrok-skip-browser-warning': 'true',
      ...options.headers
    }
  });
};

// Helper function for authenticated API calls
export const fetchAuthAPI = (url, options = {}) => {
  const token = localStorage.getItem('authToken');
  return fetchAPI(url, {
    ...options,
    headers: {
      'Authorization': token ? `Bearer ${token}` : '',
      'Content-Type': 'application/json',
      ...options.headers
    }
  });
};


