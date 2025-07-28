import axios from 'axios';
import { User } from '../contexts/AuthContext';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('vangmayam_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('vangmayam_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authService = {
  // Set auth token for requests
  setAuthToken: (token: string) => {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  },

  // Remove auth token
  removeAuthToken: () => {
    delete api.defaults.headers.common['Authorization'];
  },

  // Get current user
  getCurrentUser: async (): Promise<User> => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  // Google OAuth login
  googleLogin: async (): Promise<string> => {
    // Redirect to Google OAuth
    window.location.href = `${API_BASE_URL}/auth/google`;
    return ''; // This won't actually return since we're redirecting
  },

  // Handle OAuth callback (called from callback page)
  handleOAuthCallback: async (code: string): Promise<LoginResponse> => {
    const response = await api.get(`/auth/google/callback?code=${code}`);
    return response.data;
  },

  // Logout
  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
  },

  // Refresh token
  refreshToken: async (): Promise<LoginResponse> => {
    const response = await api.post('/auth/refresh');
    return response.data;
  },
};

export default api;
