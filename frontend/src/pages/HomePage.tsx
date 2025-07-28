import React from 'react';
import { Link } from 'react-router-dom';
import { 
  BookOpenIcon, 
  MagnifyingGlassIcon, 
  BookmarkIcon,
  AcademicCapIcon,
  GlobeAltIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext.tsx';

const HomePage: React.FC = () => {
  const { isAuthenticated, user } = useAuth();

  const features = [
    {
      name: 'Digital Manuscripts',
      description: 'Access over 100,000 digitized Vedic texts with high-quality scans and OCR.',
      icon: BookOpenIcon,
      href: '/books',
    },
    {
      name: 'Advanced Search',
      description: 'Search across Sanskrit texts with intelligent analyzers and fuzzy matching.',
      icon: MagnifyingGlassIcon,
      href: '/search',
    },
    {
      name: 'Sanskrit Glossary',
      description: 'Comprehensive dictionary with etymology, pronunciation, and definitions.',
      icon: BookmarkIcon,
      href: '/glossary',
    },
    {
      name: 'Scholarly Tools',
      description: 'Collaborative proofreading, annotations, and citation generation.',
      icon: AcademicCapIcon,
      href: '/books',
    },
    {
      name: 'Global Access',
      description: 'Multi-device responsive interface with offline reading capabilities.',
      icon: GlobeAltIcon,
      href: '/books',
    },
    {
      name: 'Preservation',
      description: 'ALTO-compliant OCR storage and archival-standard digitization.',
      icon: ShieldCheckIcon,
      href: '/books',
    },
  ];

  const stats = [
    { name: 'Manuscripts', value: '100,000+' },
    { name: 'Pages Digitized', value: '1M+' },
    { name: 'Languages', value: '12' },
    { name: 'Scholars', value: '500+' },
  ];

  return (
    <div className="bg-white">
      {/* Hero section */}
      <div className="relative bg-gradient-to-br from-saffron-50 via-white to-sandalwood-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-6">
              <span className="block">वाङ्मयम्</span>
              <span className="block text-2xl sm:text-3xl lg:text-4xl text-saffron-600 mt-2">
                The Vedic Corpus Portal
              </span>
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
              Preserving ancient wisdom through modern technology. Access, search, and study 
              the world's largest digital collection of Vedic literature with AI-powered tools 
              and collaborative features.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/books"
                className="btn-primary text-lg px-8 py-3"
              >
                Explore Manuscripts
              </Link>
              <Link
                to="/search"
                className="btn-outline text-lg px-8 py-3"
              >
                Advanced Search
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Stats section */}
      <div className="bg-saffron-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {stats.map((stat) => (
              <div key={stat.name} className="text-center">
                <div className="text-3xl font-bold text-white">{stat.value}</div>
                <div className="text-saffron-100 mt-1">{stat.name}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Features section */}
      <div className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Comprehensive Digital Preservation
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Advanced AI-powered tools for scholars, researchers, and enthusiasts 
              to explore the rich heritage of Vedic literature.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <Link
                  key={feature.name}
                  to={feature.href}
                  className="card-hover group"
                >
                  <div className="flex items-center mb-4">
                    <div className="w-12 h-12 bg-saffron-100 rounded-lg flex items-center justify-center group-hover:bg-saffron-200 transition-colors duration-200">
                      <Icon className="w-6 h-6 text-saffron-600" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 ml-4">
                      {feature.name}
                    </h3>
                  </div>
                  <p className="text-gray-600">
                    {feature.description}
                  </p>
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      {/* Welcome section for authenticated users */}
      {isAuthenticated && user && (
        <div className="bg-white py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="bg-gradient-to-r from-saffron-500 to-vermillion-500 rounded-2xl p-8 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold mb-2">
                    स्वागतम् (Svāgatam), {user.name}!
                  </h2>
                  <p className="text-saffron-100 mb-4">
                    Welcome back to your digital Sanskrit library. Continue your scholarly journey.
                  </p>
                  <div className="flex flex-wrap gap-3">
                    <Link
                      to="/books"
                      className="bg-white text-saffron-600 px-4 py-2 rounded-lg font-medium hover:bg-saffron-50 transition-colors duration-200"
                    >
                      My Library
                    </Link>
                    {user.role !== 'reader' && (
                      <Link
                        to="/books?status=processing"
                        className="bg-saffron-400 text-white px-4 py-2 rounded-lg font-medium hover:bg-saffron-300 transition-colors duration-200"
                      >
                        Pending Reviews
                      </Link>
                    )}
                  </div>
                </div>
                <div className="hidden lg:block">
                  <div className="text-right">
                    <div className="text-sm text-saffron-100">Your Role</div>
                    <div className="text-lg font-semibold capitalize">{user.role}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Mission section */}
      <div className="bg-sandalwood-50 py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-6">
                Our Mission
              </h2>
              <p className="text-lg text-gray-600 mb-6">
                Vaidika Samrakshana Parishad is dedicated to preserving and digitizing 
                Vedic literature for global scholarly access and cultural heritage conservation. 
                Through cutting-edge AI technology and collaborative workflows, we're building 
                the world's most comprehensive digital repository of ancient wisdom.
              </p>
              <div className="space-y-4">
                <div className="flex items-start">
                  <div className="w-2 h-2 bg-saffron-600 rounded-full mt-2 mr-3"></div>
                  <p className="text-gray-600">
                    <strong>Preservation:</strong> Safeguarding irreplaceable manuscripts for future generations
                  </p>
                </div>
                <div className="flex items-start">
                  <div className="w-2 h-2 bg-saffron-600 rounded-full mt-2 mr-3"></div>
                  <p className="text-gray-600">
                    <strong>Accessibility:</strong> Making ancient texts available to scholars worldwide
                  </p>
                </div>
                <div className="flex items-start">
                  <div className="w-2 h-2 bg-saffron-600 rounded-full mt-2 mr-3"></div>
                  <p className="text-gray-600">
                    <strong>Innovation:</strong> Combining traditional scholarship with modern technology
                  </p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-2xl p-8 shadow-lg">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">
                Join Our Community
              </h3>
              <p className="text-gray-600 mb-6">
                Connect with scholars, researchers, and enthusiasts from around the world. 
                Contribute to the preservation of Vedic heritage through collaborative proofreading, 
                tagging, and scholarly annotations.
              </p>
              {!isAuthenticated ? (
                <Link
                  to="/login"
                  className="btn-primary w-full text-center"
                >
                  Get Started
                </Link>
              ) : (
                <Link
                  to="/profile"
                  className="btn-primary w-full text-center"
                >
                  View Profile
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
