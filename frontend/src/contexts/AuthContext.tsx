import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import toast from 'react-hot-toast';
import { authService } from '../services/authService.ts';

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'editor' | 'reader' | 'scholar';
  is_active: boolean;
  google_id?: string;
  created_at: string;
  updated_at: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (token: string) => void;
  logout: () => void;
  hasRole: (role: string) => boolean;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('vangmayam_token')
  );
  const queryClient = useQueryClient();

  // Fetch current user
  const {
    data: user,
    isLoading,
    error,
  } = useQuery(
    ['auth', 'me'],
    () => authService.getCurrentUser(),
    {
      enabled: !!token,
      retry: false,
      onError: () => {
        // Token is invalid, clear it
        localStorage.removeItem('vangmayam_token');
        setToken(null);
      },
    }
  );

  // Logout mutation
  const logoutMutation = useMutation(
    () => authService.logout(),
    {
      onSuccess: () => {
        localStorage.removeItem('vangmayam_token');
        setToken(null);
        queryClient.clear();
        toast.success('Logged out successfully');
      },
      onError: () => {
        // Even if logout fails on server, clear local state
        localStorage.removeItem('vangmayam_token');
        setToken(null);
        queryClient.clear();
      },
    }
  );

  const login = (newToken: string) => {
    localStorage.setItem('vangmayam_token', newToken);
    setToken(newToken);
    queryClient.invalidateQueries(['auth', 'me']);
  };

  const logout = () => {
    logoutMutation.mutate();
  };

  const hasRole = (role: string): boolean => {
    if (!user) return false;
    
    const roleHierarchy = {
      admin: ['admin', 'editor', 'scholar', 'reader'],
      editor: ['editor', 'scholar', 'reader'],
      scholar: ['scholar', 'reader'],
      reader: ['reader'],
    };
    
    return roleHierarchy[user.role as keyof typeof roleHierarchy]?.includes(role) || false;
  };

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    
    const permissions = {
      admin: [
        'manage_users', 'manage_books', 'manage_tags', 
        'proofread', 'export', 'view_audit_logs'
      ],
      editor: [
        'manage_books', 'manage_tags', 'proofread', 'export'
      ],
      scholar: [
        'proofread', 'export', 'advanced_search'
      ],
      reader: [
        'view_books', 'basic_search', 'export'
      ]
    };
    
    return permissions[user.role as keyof typeof permissions]?.includes(permission) || false;
  };

  // Set up axios interceptor for auth token
  useEffect(() => {
    if (token) {
      authService.setAuthToken(token);
    } else {
      authService.removeAuthToken();
    }
  }, [token]);

  const value: AuthContextType = {
    user: user || null,
    isLoading,
    isAuthenticated: !!user && !!token,
    login,
    logout,
    hasRole,
    hasPermission,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
