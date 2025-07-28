#!/bin/bash

# Vāṇmayam MVP - Oracle Cloud Deployment Script
# This script deploys the application to Oracle Cloud VPS

set -e

# Check required environment variables
if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    echo "❌ Error: Required environment variables not set!"
    echo "Please set the following environment variables before running this script:"
    echo "  export GOOGLE_CLIENT_ID='your-google-client-id'"
    echo "  export GOOGLE_CLIENT_SECRET='your-google-client-secret'"
    echo ""
    echo "You can find these values in your Google Cloud Console:"
    echo "https://console.cloud.google.com/apis/credentials"
    exit 1
fi

echo "✅ Environment variables verified"

# Configuration
SERVER_IP="144.24.150.159"
SERVER_USER="ubuntu"
APP_DIR="/var/www/vangmayam-mvp"
DOMAIN="vaangmayam.vsparishad.in"

echo "🚀 Starting Vāṇmayam MVP Deployment to Oracle Cloud..."

# Function to run commands on remote server
run_remote() {
    ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "$1"
}

# Function to copy files to remote server
copy_to_remote() {
    scp -o StrictHostKeyChecking=no -r "$1" $SERVER_USER@$SERVER_IP:"$2"
}

echo "📋 Step 1: Preparing deployment package..."

# Create deployment package (excluding sensitive files)
TEMP_DIR=$(mktemp -d)
rsync -av --exclude='.git' \
          --exclude='node_modules' \
          --exclude='__pycache__' \
          --exclude='*.pyc' \
          --exclude='.env' \
          --exclude='.env.production' \
          --exclude='backend/credentials' \
          --exclude='postgres_data' \
          --exclude='redis_data' \
          --exclude='elasticsearch_data' \
          --exclude='minio_data' \
          --exclude='frontend/build' \
          . "$TEMP_DIR/vangmayam-mvp/"

echo "📁 Step 2: Copying files to server..."

# Create application directory on server
run_remote "sudo mkdir -p $APP_DIR && sudo chown $SERVER_USER:$SERVER_USER $APP_DIR"

# Copy application files
copy_to_remote "$TEMP_DIR/vangmayam-mvp/*" "$APP_DIR/"

echo "🔧 Step 3: Setting up backend environment..."

# Copy production environment files (you'll need to create these manually on server)
cat > "$TEMP_DIR/setup_env.sh" << 'EOF'
#!/bin/bash
cd /var/www/vangmayam-mvp

# Create backend production environment
cat > backend/.env.production << 'BACKEND_ENV'
# Vāṇmayam MVP - Backend Production Environment
APP_NAME=Vāṇmayam - Vedic Corpus Portal
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production

# Server Configuration
HOST=0.0.0.0
PORT=8001

# URLs - Production
FRONTEND_URL=https://vaangmayam.vsparishad.in
BACKEND_URL=https://vaangmayam.vsparishad.in
API_BASE_URL=https://vaangmayam.vsparishad.in/api/v1

# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vangmayam
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vangmayam
DB_USER=postgres
DB_PASSWORD=postgres

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Elasticsearch Configuration
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200

# MinIO Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=vangmayam-documents
MINIO_SECURE=false

# Security Configuration
SECRET_KEY=your-super-secret-production-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth 2.0 Configuration - Production
# These will be set from environment variables during deployment
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
GOOGLE_REDIRECT_URI=https://vaangmayam.vsparishad.in/api/v1/auth/google/callback

# CORS Configuration - Production
CORS_ORIGINS=https://vaangmayam.vsparishad.in,https://vsparishad.in

# OCR Settings
OCR_DPI=400
OCR_LANGUAGE=san
OCR_OUTPUT_FORMAT=alto

# Feature Flags
ENABLE_MOCK_LOGIN=false
ENABLE_ADMIN_ENDPOINTS=true
ENABLE_STARDICT_IMPORT=true
BACKEND_ENV

# Create frontend production environment
cat > frontend/.env.production << 'FRONTEND_ENV'
# Vāṇmayam MVP - Frontend Production Environment
REACT_APP_API_BASE_URL=https://vaangmayam.vsparishad.in/api/v1
REACT_APP_BACKEND_URL=https://vaangmayam.vsparishad.in/api
REACT_APP_FRONTEND_URL=https://vaangmayam.vsparishad.in

# Authentication Configuration - Production
REACT_APP_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
REACT_APP_AUTH_REDIRECT_URI=https://vaangmayam.vsparishad.in/auth/callback

# Application Configuration
REACT_APP_APP_NAME=Vāṇmayam - Vedic Corpus Portal
REACT_APP_APP_VERSION=1.0.0
REACT_APP_ENVIRONMENT=production

# Feature Flags
REACT_APP_ENABLE_MOCK_LOGIN=false
REACT_APP_ENABLE_ADMIN_FEATURES=true
REACT_APP_ENABLE_STARDICT_IMPORT=true
REACT_APP_ENABLE_COLLABORATIVE_EDITING=true
REACT_APP_ENABLE_ADVANCED_SEARCH=true

# Upload Configuration
REACT_APP_MAX_FILE_SIZE=50MB
REACT_APP_ALLOWED_FILE_TYPES=.pdf,.png,.jpg,.jpeg,.tiff
REACT_APP_MAX_FILES_PER_UPLOAD=10

# Search Configuration
REACT_APP_SEARCH_RESULTS_PER_PAGE=20
REACT_APP_SEARCH_HIGHLIGHT_ENABLED=true
REACT_APP_SEARCH_AUTOCOMPLETE_ENABLED=true

# Performance Configuration
REACT_APP_ENABLE_SERVICE_WORKER=true
REACT_APP_ENABLE_LAZY_LOADING=true
REACT_APP_DEBOUNCE_SEARCH_MS=300

# Production Configuration
GENERATE_SOURCEMAP=false
REACT_APP_DEBUG_MODE=false
FRONTEND_ENV

echo "✅ Environment files created successfully!"
EOF

copy_to_remote "$TEMP_DIR/setup_env.sh" "/tmp/"
run_remote "chmod +x /tmp/setup_env.sh && /tmp/setup_env.sh"

echo "🐳 Step 4: Setting up Docker services..."

# Start Docker services
run_remote "cd $APP_DIR && docker-compose up -d postgres redis elasticsearch minio"

echo "⏳ Waiting for services to start..."
sleep 30

echo "🐍 Step 5: Setting up Python backend..."

# Set up Python virtual environment and install dependencies
run_remote "cd $APP_DIR/backend && python3.11 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"

echo "⚛️ Step 6: Building React frontend..."

# Install Node.js dependencies and build frontend
run_remote "cd $APP_DIR/frontend && npm install && npm run build"

echo "🌐 Step 7: Configuring Nginx..."

# Create Nginx configuration
cat > "$TEMP_DIR/nginx_config" << 'EOF'
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
EOF

copy_to_remote "$TEMP_DIR/nginx_config" "/tmp/"
run_remote "sudo cp /tmp/nginx_config /etc/nginx/sites-available/vangmayam && sudo ln -sf /etc/nginx/sites-available/vangmayam /etc/nginx/sites-enabled/ && sudo nginx -t"

echo "🔒 Step 8: Setting up SSL certificate..."

# Get SSL certificate
run_remote "sudo certbot --nginx -d vaangmayam.vsparishad.in --non-interactive --agree-tos --email vsparishad@gmail.com"

echo "🚀 Step 9: Starting application services..."

# Create systemd service for backend
cat > "$TEMP_DIR/vangmayam-backend.service" << 'EOF'
[Unit]
Description=Vāṇmayam MVP Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/var/www/vangmayam-mvp/backend
Environment=PATH=/var/www/vangmayam-mvp/backend/venv/bin
ExecStart=/var/www/vangmayam-mvp/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --env-file .env.production
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

copy_to_remote "$TEMP_DIR/vangmayam-backend.service" "/tmp/"
run_remote "sudo cp /tmp/vangmayam-backend.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable vangmayam-backend && sudo systemctl start vangmayam-backend"

echo "🔄 Step 10: Restarting services..."

# Restart Nginx
run_remote "sudo systemctl restart nginx"

echo "🎉 Deployment completed successfully!"
echo ""
echo "🌐 Your Vāṇmayam MVP is now live at: https://vaangmayam.vsparishad.in"
echo ""
echo "📋 Next steps:"
echo "1. Verify DNS: Make sure vaangmayam.vsparishad.in points to $SERVER_IP"
echo "2. Check services: ssh $SERVER_USER@$SERVER_IP 'sudo systemctl status vangmayam-backend nginx'"
echo "3. View logs: ssh $SERVER_USER@$SERVER_IP 'sudo journalctl -u vangmayam-backend -f'"
echo "4. Test the application: Visit https://vaangmayam.vsparishad.in"
echo ""
echo "🔧 Troubleshooting:"
echo "- Backend logs: sudo journalctl -u vangmayam-backend -f"
echo "- Nginx logs: sudo tail -f /var/log/nginx/error.log"
echo "- SSL renewal: sudo certbot renew --dry-run"

# Cleanup
rm -rf "$TEMP_DIR"

echo "✅ Deployment script completed!"
