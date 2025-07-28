#!/bin/bash

# Vāṇmayam MVP - Local Server Deployment Script
# This script runs directly on the Oracle Cloud VPS and handles complete deployment
# with comprehensive validation checks and error handling

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="vaangmayam.vsparishad.in"
APP_DIR="/var/www/vangmayam-mvp"
BACKEND_PORT=8001
NGINX_CONFIG="/etc/nginx/sites-available/vangmayam"
SERVICE_NAME="vangmayam-backend"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if service is running
service_running() {
    systemctl is-active --quiet "$1"
}

# Function to check if port is available
port_available() {
    ! netstat -tuln | grep -q ":$1 "
}

# Function to validate environment file
validate_env_file() {
    local env_file="$1"
    local required_vars="$2"
    
    if [[ ! -f "$env_file" ]]; then
        error "Environment file not found: $env_file"
        return 1
    fi
    
    log "Validating environment file: $env_file"
    
    for var in $required_vars; do
        if ! grep -q "^$var=" "$env_file"; then
            error "Required environment variable '$var' not found in $env_file"
            return 1
        fi
        
        # Check if variable has a value
        local value=$(grep "^$var=" "$env_file" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
        if [[ -z "$value" || "$value" == "your-"* ]]; then
            error "Environment variable '$var' has placeholder or empty value in $env_file"
            return 1
        fi
    done
    
    log "✅ Environment file validation passed: $env_file"
    return 0
}

# Function to check system requirements
check_system_requirements() {
    log "🔍 Checking system requirements..."
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        error "Cannot determine OS version"
        exit 1
    fi
    
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        error "This script is designed for Ubuntu. Detected: $ID"
        exit 1
    fi
    
    log "✅ OS: Ubuntu $VERSION_ID"
    
    # Check architecture
    local arch=$(uname -m)
    if [[ "$arch" != "aarch64" && "$arch" != "x86_64" ]]; then
        warning "Untested architecture: $arch (expected aarch64 for Oracle Cloud ARM64)"
    fi
    log "✅ Architecture: $arch"
    
    # Check available disk space (minimum 5GB)
    local available_space=$(df / | awk 'NR==2 {print $4}')
    local min_space=5242880  # 5GB in KB
    if [[ $available_space -lt $min_space ]]; then
        error "Insufficient disk space. Available: $(($available_space/1024/1024))GB, Required: 5GB"
        exit 1
    fi
    log "✅ Disk space: $(($available_space/1024/1024))GB available"
    
    # Check memory (minimum 1GB)
    local total_mem=$(free -m | awk 'NR==2{print $2}')
    if [[ $total_mem -lt 1024 ]]; then
        warning "Low memory detected: ${total_mem}MB (recommended: 2GB+)"
    fi
    log "✅ Memory: ${total_mem}MB"
}

# Function to check network connectivity
check_network() {
    log "🌐 Checking network connectivity..."
    
    # Check internet connectivity
    if ! ping -c 1 google.com >/dev/null 2>&1; then
        error "No internet connectivity"
        exit 1
    fi
    log "✅ Internet connectivity"
    
    # Check DNS resolution for domain
    if ! nslookup "$DOMAIN" >/dev/null 2>&1; then
        warning "DNS resolution failed for $DOMAIN - SSL certificate may fail"
    else
        local resolved_ip=$(nslookup "$DOMAIN" | grep -A1 "Name:" | tail -1 | awk '{print $2}')
        local server_ip=$(curl -s ifconfig.me)
        if [[ "$resolved_ip" != "$server_ip" ]]; then
            warning "Domain $DOMAIN resolves to $resolved_ip but server IP is $server_ip"
        else
            log "✅ DNS correctly configured: $DOMAIN -> $server_ip"
        fi
    fi
}

# Function to install system dependencies
install_system_dependencies() {
    log "📦 Installing system dependencies..."
    
    # Update package list
    sudo apt update
    
    # Install essential packages
    local packages=(
        "curl" "wget" "git" "nginx" "certbot" "python3-certbot-nginx"
        "ufw" "fail2ban" "htop" "tree" "unzip" "software-properties-common"
        "apt-transport-https" "ca-certificates" "gnupg" "lsb-release"
        "python3.11" "python3.11-venv" "python3.11-dev" "python3-pip"
        "postgresql-client" "redis-tools"
    )
    
    for package in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            log "Installing $package..."
            sudo apt install -y "$package"
        else
            log "✅ $package already installed"
        fi
    done
}

# Function to install Docker
install_docker() {
    log "🐳 Installing Docker..."
    
    if command_exists docker; then
        log "✅ Docker already installed: $(docker --version)"
        return 0
    fi
    
    # Install Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    
    # Install Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    log "✅ Docker installed: $(docker --version)"
    log "✅ Docker Compose installed: $(docker-compose --version)"
}

# Function to install Node.js
install_nodejs() {
    log "⚛️ Installing Node.js..."
    
    if command_exists node; then
        local node_version=$(node --version)
        log "✅ Node.js already installed: $node_version"
        return 0
    fi
    
    # Install Node.js 18.x
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
    
    log "✅ Node.js installed: $(node --version)"
    log "✅ npm installed: $(npm --version)"
}

# Function to configure firewall
configure_firewall() {
    log "🔒 Configuring firewall..."
    
    # Configure UFW
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 'Nginx Full'
    sudo ufw --force enable
    
    log "✅ Firewall configured"
    
    # Configure Fail2Ban
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
    
    log "✅ Fail2Ban configured"
}

# Function to validate environment files
validate_environment_files() {
    log "🔍 Validating environment files..."
    
    # Required backend environment variables
    local backend_vars="APP_NAME ENVIRONMENT FRONTEND_URL BACKEND_URL DATABASE_URL REDIS_URL ELASTICSEARCH_URL SECRET_KEY GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET"
    
    # Required frontend environment variables
    local frontend_vars="REACT_APP_API_BASE_URL REACT_APP_FRONTEND_URL REACT_APP_GOOGLE_CLIENT_ID REACT_APP_ENVIRONMENT"
    
    # Validate backend environment
    if ! validate_env_file "$APP_DIR/backend/.env.production" "$backend_vars"; then
        error "Backend environment validation failed"
        exit 1
    fi
    
    # Validate frontend environment
    if ! validate_env_file "$APP_DIR/frontend/.env.production" "$frontend_vars"; then
        error "Frontend environment validation failed"
        exit 1
    fi
    
    # Check for placeholder values
    if grep -q "your-" "$APP_DIR/backend/.env.production" "$APP_DIR/frontend/.env.production"; then
        error "Placeholder values found in environment files. Please update with actual values."
        exit 1
    fi
    
    log "✅ All environment files validated"
}

# Function to start Docker services
start_docker_services() {
    log "🐳 Starting Docker services..."
    
    cd "$APP_DIR"
    
    # Check if docker-compose.yml exists
    if [[ ! -f "docker-compose.yml" ]]; then
        error "docker-compose.yml not found in $APP_DIR"
        exit 1
    fi
    
    # Start services
    docker-compose up -d postgres redis elasticsearch minio
    
    # Wait for services to be ready
    log "⏳ Waiting for services to start..."
    sleep 30
    
    # Validate services
    local services=("postgres" "redis" "elasticsearch" "minio")
    for service in "${services[@]}"; do
        if ! docker-compose ps | grep -q "${service}.*Up"; then
            error "Service $service failed to start"
            docker-compose logs "$service"
            exit 1
        fi
        log "✅ $service service running"
    done
    
    # Test database connection
    if ! docker-compose exec -T postgres pg_isready -U postgres; then
        error "PostgreSQL is not ready"
        exit 1
    fi
    log "✅ PostgreSQL connection verified"
    
    # Test Redis connection
    if ! docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        error "Redis is not responding"
        exit 1
    fi
    log "✅ Redis connection verified"
    
    # Test Elasticsearch
    if ! curl -s http://localhost:9200/_cluster/health | grep -q "yellow\|green"; then
        error "Elasticsearch is not healthy"
        exit 1
    fi
    log "✅ Elasticsearch connection verified"
}

# Function to setup Python backend
setup_backend() {
    log "🐍 Setting up Python backend..."
    
    cd "$APP_DIR/backend"
    
    # Create virtual environment
    if [[ ! -d "venv" ]]; then
        python3.11 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Test import of main modules
    python -c "
import sys
sys.path.append('.')
try:
    from app.main import app
    from app.core.config import settings
    print('✅ Backend modules import successfully')
except Exception as e:
    print(f'❌ Backend import error: {e}')
    sys.exit(1)
"
    
    log "✅ Backend setup completed"
}

# Function to build frontend
build_frontend() {
    log "⚛️ Building React frontend..."
    
    cd "$APP_DIR/frontend"
    
    # Install dependencies
    npm install
    
    # Build for production
    NODE_ENV=production npm run build
    
    # Verify build
    if [[ ! -d "build" ]] || [[ ! -f "build/index.html" ]]; then
        error "Frontend build failed - build directory or index.html not found"
        exit 1
    fi
    
    local build_size=$(du -sh build | cut -f1)
    log "✅ Frontend build completed (size: $build_size)"
}

# Function to configure Nginx
configure_nginx() {
    log "🌐 Configuring Nginx..."
    
    # Create Nginx configuration
    sudo tee "$NGINX_CONFIG" > /dev/null << EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN;

    # SSL configuration will be added by Certbot
ssl_certificate /etc/letsencrypt/live/vaangmayam.vsparishad.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vaangmayam.vsparishad.in/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Frontend - serve from root
    location / {
        root $APP_DIR/frontend/build;
        try_files \$uri \$uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API endpoints
    location /api {
        proxy_pass http://127.0.0.1:$BACKEND_PORT/api;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:$BACKEND_PORT/health;
        access_log off;
    }
}
EOF

    # Enable site
    sudo ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/
    
    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test Nginx configuration
    if ! sudo nginx -t; then
        error "Nginx configuration test failed"
        exit 1
    fi
    
    log "✅ Nginx configured"
}

# Function to setup SSL certificate
setup_ssl() {
    log "🔒 Setting up SSL certificate..."
    
    # Check if certificate already exists
    if [[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
        log "✅ SSL certificate already exists for $DOMAIN"
        return 0
    fi
    
    # Get SSL certificate
    sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "vsparishad@gmail.com"
    
    if [[ $? -eq 0 ]]; then
        log "✅ SSL certificate obtained successfully"
        
        # Test certificate renewal
        sudo certbot renew --dry-run
        log "✅ SSL certificate renewal test passed"
    else
        error "SSL certificate setup failed"
        exit 1
    fi
}

# Function to create systemd service
create_systemd_service() {
    log "⚙️ Creating systemd service..."
    
    sudo tee "/etc/systemd/system/$SERVICE_NAME.service" > /dev/null << EOF
[Unit]
Description=Vāṇmayam MVP Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=$APP_DIR/backend
Environment=PATH=$APP_DIR/backend/venv/bin
EnvironmentFile=$APP_DIR/backend/.env.production
ExecStart=$APP_DIR/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    
    log "✅ Systemd service created"
}

# Function to start services
start_services() {
    log "🚀 Starting services..."
    
    # Start backend service
    sudo systemctl start "$SERVICE_NAME"
    
    # Wait for backend to start
    sleep 10
    
    # Check backend service status
    if ! service_running "$SERVICE_NAME"; then
        error "Backend service failed to start"
        sudo journalctl -u "$SERVICE_NAME" --no-pager -n 20
        exit 1
    fi
    log "✅ Backend service started"
    
    # Test backend health
    local health_url="http://localhost:$BACKEND_PORT/api/v1/health"
    if ! curl -f -s "$health_url" >/dev/null; then
        error "Backend health check failed"
        sudo journalctl -u "$SERVICE_NAME" --no-pager -n 20
        exit 1
    fi
    log "✅ Backend health check passed"
    
    # Restart Nginx
    sudo systemctl restart nginx
    
    if ! service_running "nginx"; then
        error "Nginx failed to start"
        sudo journalctl -u nginx --no-pager -n 20
        exit 1
    fi
    log "✅ Nginx restarted"
}

# Function to run deployment tests
run_deployment_tests() {
    log "🧪 Running deployment tests..."
    
    # Test HTTP redirect
    local http_response=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN")
    if [[ "$http_response" != "301" ]]; then
        warning "HTTP to HTTPS redirect test failed (got $http_response, expected 301)"
    else
        log "✅ HTTP to HTTPS redirect working"
    fi
    
    # Test HTTPS
    local https_response=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN")
    if [[ "$https_response" != "200" ]]; then
        error "HTTPS test failed (got $https_response, expected 200)"
    else
        log "✅ HTTPS working"
    fi
    
    # Test API health endpoint
    local api_response=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/api/v1/health")
    if [[ "$api_response" != "200" ]]; then
        error "API health check failed (got $api_response, expected 200)"
    else
        log "✅ API health check working"
    fi
    
    # Test frontend
    if curl -s "https://$DOMAIN" | grep -q "Vāṇmayam"; then
        log "✅ Frontend loading correctly"
    else
        warning "Frontend may not be loading correctly"
    fi
}

# Function to display deployment summary
display_summary() {
    log "📋 Deployment Summary"
    echo
    echo "🎉 Vāṇmayam MVP deployment completed successfully!"
    echo
    echo "📍 Application URLs:"
    echo "   • Main Application: https://$DOMAIN"
    echo "   • API Health Check: https://$DOMAIN/api/v1/health"
    echo "   • API Documentation: https://$DOMAIN/api/v1/docs"
    echo
    echo "🔧 Service Status:"
    echo "   • Backend Service: $(systemctl is-active $SERVICE_NAME)"
    echo "   • Nginx: $(systemctl is-active nginx)"
    echo "   • PostgreSQL: $(docker-compose ps postgres | grep -q Up && echo "running" || echo "stopped")"
    echo "   • Redis: $(docker-compose ps redis | grep -q Up && echo "running" || echo "stopped")"
    echo "   • Elasticsearch: $(docker-compose ps elasticsearch | grep -q Up && echo "running" || echo "stopped")"
    echo
    echo "📊 System Resources:"
    echo "   • Disk Usage: $(df -h / | awk 'NR==2 {print $5 " used of " $2}')"
    echo "   • Memory Usage: $(free -h | awk 'NR==2{printf "%.1f%% used of %s\n", $3/$2*100, $2}')"
    echo
    echo "🔍 Useful Commands:"
    echo "   • View backend logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "   • View nginx logs: sudo tail -f /var/log/nginx/error.log"
    echo "   • Restart backend: sudo systemctl restart $SERVICE_NAME"
    echo "   • Check SSL certificate: sudo certbot certificates"
    echo
    echo "🎯 Next Steps:"
    echo "   1. Test Google OAuth login at https://$DOMAIN"
    echo "   2. Upload and process your first document"
    echo "   3. Test the Sanskrit search functionality"
    echo "   4. Import StarDict dictionaries via admin panel"
    echo
}

# Main deployment function
main() {
    log "🚀 Starting Vāṇmayam MVP deployment on Oracle Cloud VPS"
    log "📍 Domain: $DOMAIN"
    log "📁 App Directory: $APP_DIR"
    echo
    
    # Pre-deployment checks
    check_system_requirements
    check_network
    
    # Ensure we're in the correct directory
    if [[ ! -d "$APP_DIR" ]]; then
        error "Application directory not found: $APP_DIR"
        error "Please ensure the repository is cloned to $APP_DIR"
        exit 1
    fi
    
    cd "$APP_DIR"
    
    # Validate environment files
    validate_environment_files
    
    # System setup
    install_system_dependencies
    install_docker
    install_nodejs
    configure_firewall
    
    # Application setup
    start_docker_services
    setup_backend
    build_frontend
    
    # Web server setup
    configure_nginx
    setup_ssl
    
    # Service setup
    create_systemd_service
    start_services
    
    # Testing
    run_deployment_tests
    
    # Summary
    display_summary
    
    log "✅ Deployment completed successfully!"
}

# Run main function
main "$@"
