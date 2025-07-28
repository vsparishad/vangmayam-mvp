# Complete Deployment Guide for Vāṇmayam MVP
## Production Deployment on vsparishad.in/vaangmayam

This guide provides multiple deployment options for your Vāṇmayam MVP, from budget-friendly to enterprise-grade solutions.

## 🎯 Deployment Architecture Overview

```
Internet → Domain (vsparishad.in) → Hosting Provider → Your Application
                                        ↓
                               Frontend (React) + Backend (FastAPI)
                                        ↓
                               Database (PostgreSQL) + Redis + Elasticsearch
```

## 🚀 Deployment Options (Recommended Order)

### Option 1: DigitalOcean Droplet (Recommended - Best Value)
**Cost**: ~$20-40/month | **Difficulty**: Medium | **Control**: High

### Option 2: AWS/Google Cloud (Enterprise)
**Cost**: ~$50-100/month | **Difficulty**: High | **Control**: Maximum

### Option 3: Shared Hosting with Node.js (Budget)
**Cost**: ~$10-20/month | **Difficulty**: Low | **Control**: Limited

### Option 4: Netlify + Railway (Hybrid)
**Cost**: ~$15-30/month | **Difficulty**: Low | **Control**: Medium

---

## 🔥 Option 1: DigitalOcean Droplet (RECOMMENDED)

### Step 1: Create DigitalOcean Droplet
1. Go to [DigitalOcean](https://www.digitalocean.com/)
2. Create account and add payment method
3. Create Droplet:
   - **Image**: Ubuntu 22.04 LTS
   - **Size**: Basic $24/month (4GB RAM, 2 vCPUs, 80GB SSD)
   - **Region**: Choose closest to India (Bangalore if available)
   - **Authentication**: SSH Key (recommended) or Password
   - **Hostname**: `vangmayam-production`

### Step 2: Domain Configuration
1. In your domain registrar (where you bought vsparishad.in):
   ```
   A Record: @ → [Your Droplet IP]
   A Record: www → [Your Droplet IP]
   A Record: vaangmayam → [Your Droplet IP]
   ```

### Step 3: Server Setup
```bash
# Connect to your droplet
ssh root@your-droplet-ip

# Update system
apt update && apt upgrade -y

# Install required software
apt install -y nginx postgresql postgresql-contrib redis-server nodejs npm python3 python3-pip git curl

# Install Docker (for easier deployment)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### Step 4: SSL Certificate Setup
```bash
# Install Certbot for Let's Encrypt SSL
apt install -y certbot python3-certbot-nginx

# Get SSL certificate
certbot --nginx -d vsparishad.in -d www.vsparishad.in -d vaangmayam.vsparishad.in
```

### Step 5: Deploy Application
```bash
# Clone your repository
cd /var/www
git clone https://github.com/your-username/vangmayam-mvp.git
cd vangmayam-mvp

# Set up backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy production environment
cp .env.production .env
# Edit .env with your production values
nano .env

# Set up database
sudo -u postgres createdb vangmayam_prod
sudo -u postgres createuser vangmayam_user
sudo -u postgres psql -c "ALTER USER vangmayam_user PASSWORD 'your-secure-password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vangmayam_prod TO vangmayam_user;"

# Run database migrations
python -m alembic upgrade head

# Set up frontend
cd ../frontend
npm install
cp .env.production .env
# Edit .env with your production values
nano .env
npm run build
```

### Step 6: Nginx Configuration
```bash
# Create nginx config
nano /etc/nginx/sites-available/vangmayam
```

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name vsparishad.in www.vsparishad.in;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name vsparishad.in www.vsparishad.in;

    ssl_certificate /etc/letsencrypt/live/vsparishad.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vsparishad.in/privkey.pem;

    # Main site redirect to vaangmayam
    location / {
        return 301 https://vsparishad.in/vaangmayam$request_uri;
    }

    # Vāṇmayam application
    location /vaangmayam {
        alias /var/www/vangmayam-mvp/frontend/build;
        try_files $uri $uri/ /vaangmayam/index.html;
        
        # Handle React Router
        location /vaangmayam/static {
            alias /var/www/vangmayam-mvp/frontend/build/static;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API endpoints
    location /vaangmayam/api {
        proxy_pass http://127.0.0.1:8001/api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
ln -s /etc/nginx/sites-available/vangmayam /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### Step 7: Process Management with Systemd
```bash
# Create systemd service for backend
nano /etc/systemd/system/vangmayam-backend.service
```

```ini
[Unit]
Description=Vangmayam Backend API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/vangmayam-mvp/backend
Environment=PATH=/var/www/vangmayam-mvp/backend/venv/bin
ExecStart=/var/www/vangmayam-mvp/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Start services
systemctl daemon-reload
systemctl enable vangmayam-backend
systemctl start vangmayam-backend
systemctl status vangmayam-backend
```

---

## 🌐 Option 2: AWS Cloud Deployment

### Step 1: AWS Services Setup
1. **EC2 Instance**: t3.medium (2 vCPU, 4GB RAM)
2. **RDS PostgreSQL**: db.t3.micro for development
3. **ElastiCache Redis**: cache.t3.micro
4. **S3 Bucket**: For file storage
5. **CloudFront**: CDN for frontend
6. **Route 53**: DNS management

### Step 2: Infrastructure as Code (Optional)
```bash
# Install AWS CLI and Terraform
pip install awscli
# Download Terraform from terraform.io

# Create terraform configuration
mkdir aws-infrastructure
cd aws-infrastructure
```

Create `main.tf`:
```hcl
provider "aws" {
  region = "ap-south-1"  # Mumbai region
}

# VPC and networking
resource "aws_vpc" "vangmayam_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "vangmayam-vpc"
  }
}

# EC2 instance for application
resource "aws_instance" "vangmayam_app" {
  ami           = "ami-0c02fb55956c7d316"  # Ubuntu 22.04 LTS
  instance_type = "t3.medium"
  
  tags = {
    Name = "vangmayam-production"
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "vangmayam_db" {
  identifier = "vangmayam-production"
  engine     = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"
  allocated_storage = 20
  
  db_name  = "vangmayam"
  username = "vangmayam_user"
  password = "your-secure-password"
  
  skip_final_snapshot = true
}
```

---

## 💰 Option 3: Budget Shared Hosting

### Compatible Hosting Providers
1. **Hostinger** (Node.js support) - ~$10/month
2. **A2 Hosting** (Node.js support) - ~$15/month
3. **InMotion Hosting** (Node.js support) - ~$20/month

### Deployment Steps
1. **Upload Files**: Use cPanel File Manager or FTP
2. **Database Setup**: Create PostgreSQL database via hosting panel
3. **Node.js Setup**: Enable Node.js in hosting control panel
4. **Environment Variables**: Set via hosting control panel
5. **Domain Mapping**: Point vsparishad.in to hosting account

### Limitations
- Limited server control
- Shared resources
- May not support all features (Redis, Elasticsearch)

---

## 🔄 Option 4: Hybrid Deployment (Netlify + Railway)

### Frontend: Netlify
1. Connect GitHub repository to Netlify
2. Set build command: `npm run build`
3. Set publish directory: `build`
4. Configure custom domain: `vsparishad.in/vaangmayam`

### Backend: Railway
1. Connect GitHub repository to Railway
2. Set environment variables
3. Railway auto-deploys on git push

### Database: Railway PostgreSQL
1. Add PostgreSQL service in Railway
2. Get connection string
3. Update backend environment variables

---

## 🔧 Deployment Automation Scripts

### Docker Deployment (All Options)
Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile.prod
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - postgres
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    ports:
      - "3000:80"

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: vangmayam_prod
      POSTGRES_USER: vangmayam_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Deployment Script
Create `deploy.sh`:
```bash
#!/bin/bash

echo "🚀 Deploying Vāṇmayam MVP to Production..."

# Pull latest code
git pull origin main

# Build and deploy with Docker
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Run database migrations
docker-compose -f docker-compose.prod.yml exec backend python -m alembic upgrade head

echo "✅ Deployment complete!"
echo "🌐 Visit: https://vsparishad.in/vaangmayam"
```

---

## 📊 Cost Comparison

| Option | Monthly Cost | Setup Time | Maintenance | Scalability |
|--------|-------------|------------|-------------|-------------|
| DigitalOcean | $24-40 | 2-4 hours | Medium | High |
| AWS | $50-100 | 4-8 hours | High | Maximum |
| Shared Hosting | $10-20 | 1-2 hours | Low | Limited |
| Netlify + Railway | $15-30 | 1-2 hours | Low | Medium |

## 🎯 Recommendation

**For vsparishad.in/vaangmayam, I recommend Option 1 (DigitalOcean)** because:
- ✅ Best balance of cost, control, and performance
- ✅ Full server access for customization
- ✅ Reliable infrastructure
- ✅ Easy to scale
- ✅ Good for educational/research organizations

## 🚨 Pre-Deployment Checklist

- [ ] Domain vsparishad.in configured
- [ ] Google OAuth 2.0 credentials ready
- [ ] Production environment variables set
- [ ] Database backup strategy planned
- [ ] SSL certificate configured
- [ ] Monitoring and logging set up

## 📞 Need Help?

If you need assistance with any deployment option, I can provide:
1. **Detailed step-by-step guidance** for your chosen option
2. **Custom deployment scripts** for your specific setup
3. **Troubleshooting support** during deployment
4. **Performance optimization** after deployment

Choose your preferred deployment option, and I'll provide detailed implementation steps!
