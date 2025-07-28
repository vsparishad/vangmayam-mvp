# Oracle Cloud VPS Deployment Guide
## Vāṇmayam MVP on Ubuntu 22.04 ARM64

This guide provides step-by-step instructions for deploying your Vāṇmayam MVP to Oracle Cloud Infrastructure (OCI) with ARM64 architecture.

## 🎯 Deployment Approach Options

### Option 1: Guided Remote Deployment (RECOMMENDED)
- **Security**: You maintain full control of your server
- **Process**: I provide step-by-step commands, you execute them
- **Benefits**: Secure, educational, you learn the deployment process

### Option 2: Automated Deployment Scripts
- **Security**: You run pre-built scripts on your server
- **Process**: I create deployment scripts, you execute them
- **Benefits**: Fast, automated, repeatable

### Option 3: SSH-Assisted Deployment (Advanced)
- **Security**: Requires careful SSH key management
- **Process**: Temporary SSH access for deployment only
- **Benefits**: Hands-off deployment

## 🔧 Oracle Cloud ARM64 Specific Considerations

### ARM64 Architecture Compatibility
- ✅ Python 3.11+ (native ARM64 support)
- ✅ Node.js 18+ (native ARM64 support)
- ✅ PostgreSQL 15+ (native ARM64 support)
- ✅ Redis 7+ (native ARM64 support)
- ✅ Nginx (native ARM64 support)
- ✅ All Python packages (most have ARM64 wheels)

### Oracle Cloud Free Tier Benefits
- **Compute**: 4 ARM-based Ampere A1 cores (24GB RAM) - FREE forever
- **Storage**: 200GB block storage - FREE
- **Network**: 10TB outbound transfer/month - FREE
- **Perfect for**: Educational/research projects like Vāṇmayam

## 🚀 Pre-Deployment Checklist

### Oracle Cloud Setup
- [ ] OCI account created and verified
- [ ] ARM64 compute instance launched (Ubuntu 22.04)
- [ ] Security groups configured (ports 22, 80, 443)
- [ ] SSH key pair generated and configured
- [ ] Public IP assigned to instance

### Domain Configuration
- [ ] vsparishad.in DNS A record pointing to OCI public IP
- [ ] Subdomain configuration (if needed)

### Local Preparation
- [ ] Production environment files configured
- [ ] Google OAuth 2.0 credentials ready
- [ ] Database credentials prepared
- [ ] SSL certificate plan (Let's Encrypt recommended)

## 📋 Step-by-Step Deployment Commands

### Step 1: Initial Server Setup
```bash
# Connect to your Oracle Cloud instance
ssh -i ~/.ssh/your-key.pem ubuntu@your-oracle-cloud-ip

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git unzip software-properties-common

# Install Docker (ARM64 compatible)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-linux-aarch64" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version
```

### Step 2: Install Application Dependencies
```bash
# Install Node.js 18 LTS (ARM64)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python 3.11 and pip
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install PostgreSQL 15
sudo apt install -y postgresql postgresql-contrib

# Install Redis
sudo apt install -y redis-server

# Install Nginx
sudo apt install -y nginx

# Verify installations
node --version
python3.11 --version
psql --version
redis-server --version
nginx -v
```

### Step 3: Clone and Setup Application
```bash
# Create application directory
sudo mkdir -p /var/www
cd /var/www

# Clone repository (you'll need to provide the Git URL)
sudo git clone https://github.com/your-username/vangmayam-mvp.git
sudo chown -R ubuntu:ubuntu vangmayam-mvp
cd vangmayam-mvp

# Setup backend environment
cd backend
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies (ARM64 compatible)
pip install --upgrade pip
pip install -r requirements.txt

# Copy production environment
cp .env.production .env

# Setup frontend
cd ../frontend
npm install
cp .env.production .env
```

### Step 4: Database Configuration
```bash
# Configure PostgreSQL
sudo -u postgres createuser --interactive vangmayam_user
sudo -u postgres createdb vangmayam_prod
sudo -u postgres psql -c "ALTER USER vangmayam_user PASSWORD 'your-secure-password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vangmayam_prod TO vangmayam_user;"

# Update PostgreSQL configuration for remote connections
sudo nano /etc/postgresql/14/main/postgresql.conf
# Add: listen_addresses = 'localhost'

sudo nano /etc/postgresql/14/main/pg_hba.conf
# Add: local   vangmayam_prod   vangmayam_user   md5

sudo systemctl restart postgresql
```

### Step 5: SSL Certificate Setup
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate for your domain
sudo certbot --nginx -d vaangmayam.vsparishad.in

# Test automatic renewal
sudo certbot renew --dry-run
```

### Step 6: Nginx Configuration
```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/vangmayam
```

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name vaangmayam.vsparishad.in;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name vaangmayam.vsparishad.in;

    ssl_certificate /etc/letsencrypt/live/vaangmayam.vsparishad.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vaangmayam.vsparishad.in/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Vāṇmayam application - serve from root
    location / {
        root /var/www/vangmayam-mvp/frontend/build;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API endpoints
    location /api {
        proxy_pass http://127.0.0.1:8001/api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Enable site and test configuration
sudo ln -s /etc/nginx/sites-available/vangmayam /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 7: Application Services Setup
```bash
# Create systemd service for backend
sudo nano /etc/systemd/system/vangmayam-backend.service
```

```ini
[Unit]
Description=Vangmayam Backend API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/vangmayam-mvp/backend
Environment=PATH=/var/www/vangmayam-mvp/backend/venv/bin
ExecStart=/var/www/vangmayam-mvp/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Start and enable services
sudo systemctl daemon-reload
sudo systemctl enable vangmayam-backend
sudo systemctl start vangmayam-backend
sudo systemctl status vangmayam-backend
```

### Step 8: Build and Deploy Frontend
```bash
# Build React application
cd /var/www/vangmayam-mvp/frontend
npm run build

# Set proper permissions
sudo chown -R www-data:www-data /var/www/vangmayam-mvp/frontend/build
```

### Step 9: Database Migration
```bash
# Run database migrations
cd /var/www/vangmayam-mvp/backend
source venv/bin/activate
python -m alembic upgrade head

# Create initial admin user (optional)
python -c "
from app.models.user import User, UserRole
from app.core.database import get_db
import asyncio

async def create_admin():
    async for db in get_db():
        admin = User(
            email='admin@vsparishad.in',
            name='Administrator',
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)
        await db.commit()
        print('Admin user created')
        break

asyncio.run(create_admin())
"
```

## 🔒 Security Hardening

### Firewall Configuration
```bash
# Install and configure UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### Fail2Ban Setup
```bash
# Install Fail2Ban
sudo apt install -y fail2ban

# Configure Fail2Ban
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true

[nginx-http-auth]
enabled = true
```

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## 📊 Monitoring Setup

### System Monitoring
```bash
# Install htop and monitoring tools
sudo apt install -y htop iotop nethogs

# Setup log rotation
sudo nano /etc/logrotate.d/vangmayam
```

```
/var/www/vangmayam-mvp/backend/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
}
```

## 🚀 Deployment Automation Script

Create `deploy.sh`:
```bash
#!/bin/bash

echo "🚀 Deploying Vāṇmayam MVP to Oracle Cloud..."

# Pull latest changes
cd /var/www/vangmayam-mvp
git pull origin main

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head

# Update frontend
cd ../frontend
npm install
npm run build

# Restart services
sudo systemctl restart vangmayam-backend
sudo systemctl reload nginx

echo "✅ Deployment complete!"
echo "🌐 Visit: https://vsparishad.in/vaangmayam"
```

## 🎯 My Recommendation for You

**I recommend Option 1: Guided Remote Deployment** where:

1. **You maintain full control** of your Oracle Cloud server
2. **I provide step-by-step commands** that you execute
3. **We can troubleshoot together** in real-time
4. **You learn the deployment process** for future updates
5. **Maximum security** - no SSH access sharing needed

## 📞 Ready to Deploy?

To proceed with deployment, I need:

1. **Your Oracle Cloud instance details**:
   - Public IP address
   - SSH key information (just confirm you have it, don't share)
   - Instance specifications

2. **Domain configuration status**:
   - Is vsparishad.in pointing to your Oracle Cloud IP?

3. **Google OAuth 2.0 credentials**:
   - Have you set them up for production URLs?

4. **Preferred deployment method**:
   - Guided step-by-step (recommended)
   - Automated scripts
   - Other preference

Once you provide these details, I can guide you through the entire deployment process step-by-step! The Oracle Cloud ARM64 setup is perfect for your Vāṇmayam project.
