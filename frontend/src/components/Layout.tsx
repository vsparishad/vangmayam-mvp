import React from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  BookOpenIcon, 
  MagnifyingGlassIcon, 
  BookmarkIcon,
  UserIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext.tsx';
import clsx from 'clsx';

const Layout: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const navigation = [
    { name: 'Home', href: '/', icon: BookOpenIcon },
    { name: 'Books', href: '/books', icon: BookOpenIcon },
    { name: 'Search', href: '/search', icon: MagnifyingGlassIcon },
    { name: 'Glossary', href: '/glossary', icon: BookmarkIcon },
  ];

  const userNavigation = [
    { name: 'Profile', href: '/profile', icon: UserIcon },
    ...(user?.role === 'admin' ? [{ name: 'Admin', href: '/admin', icon: Cog6ToothIcon }] : []),
  ];

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo and title */}
            <div className="flex items-center">
              <Link to="/" className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-saffron-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-lg">🕉️</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">
                    वाङ्मयम्
                  </h1>
                  <p className="text-xs text-gray-500">The Vedic Corpus Portal</p>
                </div>
              </Link>
            </div>

            {/* Navigation */}
            <nav className="hidden md:flex space-x-8">
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.href;
                
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={clsx(
                      'flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200',
                      isActive
                        ? 'text-saffron-600 bg-saffron-50'
                        : 'text-gray-700 hover:text-saffron-600 hover:bg-gray-50'
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>

            {/* User menu */}
            <div className="flex items-center space-x-4">
              {isAuthenticated ? (
                <div className="flex items-center space-x-4">
                  {/* User navigation */}
                  {userNavigation.map((item) => {
                    const Icon = item.icon;
                    const isActive = location.pathname === item.href;
                    
                    return (
                      <Link
                        key={item.name}
                        to={item.href}
                        className={clsx(
                          'flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200',
                          isActive
                            ? 'text-saffron-600 bg-saffron-50'
                            : 'text-gray-700 hover:text-saffron-600 hover:bg-gray-50'
                        )}
                      >
                        <Icon className="w-4 h-4" />
                        <span className="hidden sm:inline">{item.name}</span>
                      </Link>
                    );
                  })}

                  {/* User info and logout */}
                  <div className="flex items-center space-x-3">
                    <div className="hidden sm:block text-right">
                      <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                      <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-red-600 hover:bg-red-50 transition-colors duration-200"
                      title="Logout"
                    >
                      <ArrowRightOnRectangleIcon className="w-4 h-4" />
                      <span className="hidden sm:inline">Logout</span>
                    </button>
                  </div>
                </div>
              ) : (
                <Link
                  to="/login"
                  className="btn-primary"
                >
                  Sign In
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* Mobile navigation */}
        <div className="md:hidden border-t border-gray-200">
          <div className="px-4 py-3 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.href;
              
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={clsx(
                    'flex items-center space-x-3 px-3 py-2 rounded-md text-base font-medium transition-colors duration-200',
                    isActive
                      ? 'text-saffron-600 bg-saffron-50'
                      : 'text-gray-700 hover:text-saffron-600 hover:bg-gray-50'
                  )}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                About Vāṇmayam
              </h3>
              <p className="mt-4 text-sm text-gray-600">
                A digital preservation platform for Vedic literature, combining ancient wisdom 
                with modern technology to make sacred texts accessible to scholars worldwide.
              </p>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                Resources
              </h3>
              <ul className="mt-4 space-y-2">
                <li>
                  <Link to="/books" className="text-sm text-gray-600 hover:text-saffron-600">
                    Browse Manuscripts
                  </Link>
                </li>
                <li>
                  <Link to="/search" className="text-sm text-gray-600 hover:text-saffron-600">
                    Advanced Search
                  </Link>
                </li>
                <li>
                  <Link to="/glossary" className="text-sm text-gray-600 hover:text-saffron-600">
                    Sanskrit Glossary
                  </Link>
                </li>
              </ul>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                Organization
              </h3>
              <p className="mt-4 text-sm text-gray-600">
                <strong>Vaidika Samrakshana Parishad</strong><br />
                A registered public charitable trust dedicated to preserving 
                and digitizing Vedic literature.
              </p>
            </div>
          </div>
          
          <div className="mt-8 pt-8 border-t border-gray-200">
            <p className="text-center text-sm text-gray-500">
              © 2024 Vaidika Samrakshana Parishad. Preserving Vedic heritage through technology.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
