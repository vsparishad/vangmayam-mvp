import React, { useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.tsx';
import { authService } from '../services/authService.ts';
import toast from 'react-hot-toast';

const LoginPage: React.FC = () => {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/';

  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  // Handle OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    
    if (code) {
      handleOAuthCallback(code);
    }
  }, []);

  const handleOAuthCallback = async (code: string) => {
    try {
      const response = await authService.handleOAuthCallback(code);
      login(response.access_token);
      toast.success('Successfully logged in!');
      navigate(from, { replace: true });
    } catch (error) {
      console.error('OAuth callback error:', error);
      toast.error('Login failed. Please try again.');
    }
  };

  const handleGoogleLogin = async () => {
    try {
      await authService.googleLogin();
    } catch (error) {
      console.error('Google login error:', error);
      toast.error('Login failed. Please try again.');
    }
  };

  if (isAuthenticated) {
    return null; // Will redirect via useEffect
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-saffron-50 via-white to-sandalwood-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Logo and title */}
        <div className="text-center">
          <div className="mx-auto w-16 h-16 bg-saffron-600 rounded-2xl flex items-center justify-center mb-4">
            <span className="text-white font-bold text-2xl">🕉️</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            वाङ्मयम्
          </h1>
          <p className="text-sm text-gray-600">
            The Vedic Corpus Portal
          </p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10 border border-gray-200">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Welcome Back
            </h2>
            <p className="text-gray-600">
              Sign in to access your digital Sanskrit library
            </p>
          </div>

          <div className="space-y-6">
            {/* Google OAuth Button */}
            <button
              onClick={handleGoogleLogin}
              className="w-full flex justify-center items-center px-4 py-3 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-saffron-500 transition-colors duration-200"
            >
              <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Continue with Google
            </button>

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">
                  Secure authentication via Google OAuth
                </span>
              </div>
            </div>

            {/* Information */}
            <div className="bg-saffron-50 border border-saffron-200 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-saffron-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-saffron-800">
                    First time here?
                  </h3>
                  <div className="mt-2 text-sm text-saffron-700">
                    <p>
                      New users will be automatically registered with Reader access. 
                      Contact administrators for elevated permissions.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer links */}
          <div className="mt-8 text-center">
            <Link
              to="/"
              className="text-sm text-saffron-600 hover:text-saffron-500 font-medium"
            >
              ← Back to Home
            </Link>
          </div>
        </div>

        {/* Additional info */}
        <div className="mt-8 text-center">
          <p className="text-xs text-gray-500">
            By signing in, you agree to our terms of service and privacy policy.
            <br />
            <strong>Vaidika Samrakshana Parishad</strong> - Preserving Vedic heritage through technology.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
