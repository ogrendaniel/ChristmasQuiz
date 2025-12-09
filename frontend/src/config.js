// API configuration
// Backend ngrok URL - update this when ngrok URLs change
export const API_URL = 'https://70fdf21f3fd6.ngrok-free.app';

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
