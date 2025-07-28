# Environment Configuration Guide for Vāṇmayam MVP

This guide provides comprehensive environment setup instructions for both development and production deployment on `vsparishad.in/vaangmayam`.

## 📁 Environment Files Overview

### Backend Environment Files
- `.env` - Development configuration
- `.env.production` - Production configuration

### Frontend Environment Files
- `.env` - Development configuration
- `.env.production` - Production configuration

## 🔧 Development Setup

### 1. Backend Development (.env)
```bash
# Copy and configure backend development environment
cp backend/.env.example backend/.env
```

Key development settings:
- `ENVIRONMENT=development`
- `DEBUG=true`
- `FRONTEND_URL=http://localhost:3000`
- `BACKEND_URL=http://localhost:8001`
- `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vangmayam`

### 2. Frontend Development (.env)
```bash
# Copy and configure frontend development environment
cp frontend/.env.example frontend/.env
```

Key development settings:
- `REACT_APP_API_BASE_URL=http://localhost:8001/api/v1`
- `REACT_APP_ENABLE_MOCK_LOGIN=true`
- `REACT_APP_ENVIRONMENT=development`

## 🚀 Production Setup for vsparishad.in/vaangmayam

### 1. Backend Production (.env.production)

#### Required Configuration Changes:
```bash
# Application URLs
FRONTEND_URL=https://vsparishad.in/vaangmayam
BACKEND_URL=https://vsparishad.in/vaangmayam/api
API_BASE_URL=https://vsparishad.in/vaangmayam/api/v1

# Security - CRITICAL: Change these!
SECRET_KEY=YOUR-SECURE-SECRET-KEY-HERE
ENVIRONMENT=production
DEBUG=false

# Database - Configure your production database
DATABASE_URL=postgresql+asyncpg://username:password@your-db-host:5432/vangmayam_prod

# Google OAuth 2.0 - From Google Cloud Console
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://vsparishad.in/vaangmayam/api/v1/auth/google/callback

# CORS - Allow your production domain
CORS_ORIGINS=https://vsparishad.in,https://vsparishad.in/vaangmayam
```

### 2. Frontend Production (.env.production)

#### Required Configuration Changes:
```bash
# API Configuration
REACT_APP_API_BASE_URL=https://vsparishad.in/vaangmayam/api/v1
REACT_APP_BACKEND_URL=https://vsparishad.in/vaangmayam/api
REACT_APP_FRONTEND_URL=https://vsparishad.in/vaangmayam

# Authentication
REACT_APP_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
REACT_APP_AUTH_REDIRECT_URI=https://vsparishad.in/vaangmayam/auth/callback

# Production Settings
REACT_APP_ENVIRONMENT=production
REACT_APP_ENABLE_MOCK_LOGIN=false
REACT_APP_ENABLE_DEBUG=false
GENERATE_SOURCEMAP=false
```

## 🔐 Google OAuth 2.0 Setup

### Google Cloud Console Configuration

1. **Project Setup**:
   - Project Name: `vangmayam-production`
   - Enable Google+ API and People API

2. **OAuth Consent Screen**:
   - App Name: `Vāṇmayam - Vedic Corpus Portal`
   - Homepage URL: `https://vsparishad.in/vaangmayam`
   - Privacy Policy: `https://vsparishad.in/vaangmayam/privacy`
   - Terms of Service: `https://vsparishad.in/vaangmayam/terms`

3. **OAuth Client Configuration**:
   
   **Authorized JavaScript Origins**:
   ```
   http://localhost:3000 (development)
   http://localhost:8001 (development)
   https://vsparishad.in (production)
   https://vsparishad.in/vaangmayam (production)
   ```
   
   **Authorized Redirect URIs**:
   ```
   http://localhost:3000/auth/callback (development)
   http://localhost:8001/api/v1/auth/google/callback (development)
   https://vsparishad.in/vaangmayam/auth/callback (production)
   https://vsparishad.in/vaangmayam/api/v1/auth/google/callback (production)
   ```

## 🗄️ Database Setup

### Development Database
```bash
# PostgreSQL with Docker
docker-compose up -d postgres
```

### Production Database Options

1. **Managed Database Services**:
   - AWS RDS PostgreSQL
   - Google Cloud SQL
   - DigitalOcean Managed Database
   - Azure Database for PostgreSQL

2. **Self-Hosted Database**:
   - PostgreSQL 15+ with SSL enabled
   - Regular backups configured
   - Performance monitoring

## 📦 Deployment Checklist

### Pre-Deployment
- [ ] Domain `vsparishad.in` configured and pointing to hosting
- [ ] SSL certificate installed for HTTPS
- [ ] Production database created and configured
- [ ] Google OAuth 2.0 credentials configured
- [ ] Environment variables set in hosting platform

### Backend Deployment
- [ ] Build production Docker image
- [ ] Deploy to hosting platform (AWS, DigitalOcean, etc.)
- [ ] Configure reverse proxy (nginx)
- [ ] Set up monitoring and logging
- [ ] Run database migrations

### Frontend Deployment
- [ ] Build production React app: `npm run build`
- [ ] Deploy to static hosting (Netlify, Vercel, S3)
- [ ] Configure custom domain: `vsparishad.in/vaangmayam`
- [ ] Set up CDN for performance

## 🔍 Environment Validation

### Development Validation
```bash
# Backend health check
curl http://localhost:8001/api/v1/health

# Frontend access
curl http://localhost:3000
```

### Production Validation
```bash
# Backend health check
curl https://vsparishad.in/vaangmayam/api/v1/health

# Frontend access
curl https://vsparishad.in/vaangmayam
```

## 🛡️ Security Considerations

### Production Security
- Use strong, unique `SECRET_KEY`
- Enable HTTPS everywhere
- Configure proper CORS origins
- Set up rate limiting
- Enable security headers
- Regular security updates

### Database Security
- Use strong database passwords
- Enable SSL connections
- Restrict database access by IP
- Regular backups with encryption

## 📊 Monitoring and Logging

### Production Monitoring
- Application performance monitoring (APM)
- Error tracking (Sentry)
- Log aggregation (ELK stack)
- Uptime monitoring
- Database performance monitoring

### Development Monitoring
- Local logging with DEBUG level
- Development tools and debugging
- Mock authentication for testing

## 🚨 Troubleshooting

### Common Issues
1. **OAuth Redirect Mismatch**: Ensure redirect URIs match exactly
2. **CORS Errors**: Verify CORS_ORIGINS includes your domain
3. **Database Connection**: Check DATABASE_URL and network access
4. **SSL Issues**: Ensure proper certificate configuration

### Support Resources
- Google OAuth 2.0 Documentation
- FastAPI Documentation
- React Documentation
- PostgreSQL Documentation
