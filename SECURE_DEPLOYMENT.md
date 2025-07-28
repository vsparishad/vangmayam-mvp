# Secure Deployment Guide
## Vāṇmayam MVP - Oracle Cloud VPS

This guide provides secure deployment instructions for your Vāṇmayam MVP with proper credential management.

## 🔐 Security-First Deployment

### Prerequisites

1. **Oracle Cloud VPS**: Ubuntu 22.04 ARM64 (IP: 144.24.150.159)
2. **Domain DNS**: Point `vaangmayam.vsparishad.in` to your server IP
3. **Google OAuth Credentials**: From Google Cloud Console

## 🚀 Deployment Steps

### Step 1: Set Environment Variables

Before running the deployment script, set your Google OAuth credentials:

```bash
# Set your Google OAuth credentials (get these from Google Cloud Console)
export GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"

# Verify they are set
echo "Client ID: $GOOGLE_CLIENT_ID"
echo "Client Secret: ${GOOGLE_CLIENT_SECRET:0:10}..."
```

### Step 2: Run Deployment Script

```bash
# Make sure you're in the project directory
cd /Users/shastravid/CascadeProjects/vangmayam-mvp

# Run the deployment script
./deploy.sh
```

### Step 3: Verify Deployment

After deployment completes:

1. **Check Application**: Visit https://vaangmayam.vsparishad.in
2. **Test Authentication**: Try Google OAuth login
3. **Verify API**: Check https://vaangmayam.vsparishad.in/api/v1/health

## 🔧 Manual Deployment (Alternative)

If you prefer manual deployment, follow these steps:

### 1. Connect to Server
```bash
ssh ubuntu@144.24.150.159
```

### 2. Clone Repository
```bash
sudo mkdir -p /var/www/vangmayam-mvp
sudo chown ubuntu:ubuntu /var/www/vangmayam-mvp
cd /var/www/vangmayam-mvp
git clone https://github.com/vsparishad/vangmayam-mvp.git .
```

### 3. Create Environment Files
```bash
# Backend production environment
cp backend/.env.template backend/.env.production

# Edit with your actual credentials
nano backend/.env.production
```

Update these values in `backend/.env.production`:
- `GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com`
- `GOOGLE_CLIENT_SECRET=your-google-client-secret`
- Change `SECRET_KEY` to a secure random value
- Set `DEBUG=false`

### 4. Frontend Environment
```bash
# Frontend production environment
cp frontend/.env.template frontend/.env.production

# Edit with your credentials
nano frontend/.env.production
```

Update `REACT_APP_GOOGLE_CLIENT_ID` with your client ID.

### 5. Follow Oracle Cloud Deployment Guide

Continue with the steps in `ORACLE_CLOUD_DEPLOYMENT.md` starting from "Step 4: Deploy Application".

## 🔒 Security Best Practices

### Environment Variables
- ✅ **Never commit secrets** to Git repositories
- ✅ **Use environment variables** for sensitive data
- ✅ **Rotate credentials** regularly
- ✅ **Use strong SECRET_KEY** in production

### Server Security
- ✅ **Firewall configured** (UFW with SSH and HTTPS only)
- ✅ **Fail2Ban enabled** for brute force protection
- ✅ **SSL certificates** via Let's Encrypt
- ✅ **Regular updates** with `apt update && apt upgrade`

### Application Security
- ✅ **Google OAuth 2.0** for authentication
- ✅ **JWT tokens** with expiration
- ✅ **CORS properly configured** for your domain
- ✅ **Security headers** in Nginx configuration

## 🚨 Troubleshooting

### Common Issues

**1. Environment Variables Not Set**
```bash
# Error: Required environment variables not set!
# Solution: Export your Google OAuth credentials before running deploy.sh
```

**2. DNS Not Configured**
```bash
# Error: SSL certificate fails
# Solution: Ensure vaangmayam.vsparishad.in points to 144.24.150.159
```

**3. Service Not Starting**
```bash
# Check backend service
sudo systemctl status vangmayam-backend

# View logs
sudo journalctl -u vangmayam-backend -f
```

**4. Nginx Configuration Issues**
```bash
# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

## 📞 Support

If you encounter issues during deployment:

1. **Check logs**: `sudo journalctl -u vangmayam-backend -f`
2. **Verify services**: `sudo systemctl status nginx vangmayam-backend`
3. **Test connectivity**: `curl -I https://vaangmayam.vsparishad.in`
4. **SSL certificate**: `sudo certbot certificates`

## 🎉 Success!

Once deployed successfully, your Vāṇmayam MVP will be available at:
- **Main Application**: https://vaangmayam.vsparishad.in
- **API Health Check**: https://vaangmayam.vsparishad.in/api/v1/health
- **Admin Interface**: https://vaangmayam.vsparishad.in/admin

Your digital preservation platform for Vedic literature is now live! 🌐
