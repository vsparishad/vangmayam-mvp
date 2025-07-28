import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';

import { AuthProvider } from './contexts/AuthContext.tsx';
import Layout from './components/Layout.tsx';
import HomePage from './pages/HomePage.tsx';
import BooksPage from './pages/BooksPage.tsx';
import BookDetailPage from './pages/BookDetailPage.tsx';
import SearchPage from './pages/SearchPage.tsx';
import GlossaryPage from './pages/GlossaryPage.tsx';
import LoginPage from './pages/LoginPage.tsx';
import ProfilePage from './pages/ProfilePage.tsx';
import AdminPage from './pages/AdminPage.tsx';
import ProtectedRoute from './components/ProtectedRoute.tsx';

import './index.css';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <div className="min-h-screen bg-gray-50">
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/" element={<Layout />}>
                <Route index element={<HomePage />} />
                <Route path="books" element={<BooksPage />} />
                <Route path="books/:bookId" element={<BookDetailPage />} />
                <Route path="search" element={<SearchPage />} />
                <Route path="glossary" element={<GlossaryPage />} />
                <Route
                  path="profile"
                  element={
                    <ProtectedRoute>
                      <ProfilePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="admin"
                  element={
                    <ProtectedRoute requiredRole="admin">
                      <AdminPage />
                    </ProtectedRoute>
                  }
                />
              </Route>
            </Routes>
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: '#363636',
                  color: '#fff',
                },
                success: {
                  style: {
                    background: '#059669',
                  },
                },
                error: {
                  style: {
                    background: '#dc2626',
                  },
                },
              }}
            />
          </div>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
