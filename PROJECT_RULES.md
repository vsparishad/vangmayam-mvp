# Vāṇmayam MVP - Project Rules & Deployment Learnings

## 📋 **Overview**

This document captures critical rules, best practices, and lessons learned from the Vāṇmayam MVP development and deployment process. These rules are derived from real-world deployment challenges and their solutions.

---

## 🚀 **Deployment Rules**

### **Rule 1: Environment Configuration**
- **ALWAYS** create complete `.env.production` files with ALL required variables
- **NEVER** leave placeholder values (e.g., `your-secret-key`) in production
- **MUST INCLUDE** these critical variables:
  ```bash
  DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vangmayam?sslmode=disable
  REDIS_URL=redis://localhost:6379/0
  ELASTICSEARCH_URL=http://localhost:9200
  SECRET_KEY=<actual-secure-key>
  GOOGLE_CLIENT_ID=<actual-client-id>
  GOOGLE_CLIENT_SECRET=<actual-client-secret>
  ```

### **Rule 2: Database Connection**
- **ALWAYS** use `?sslmode=disable` for local Docker PostgreSQL connections
- **NEVER** rely on SSL certificates for containerized databases
- **ALWAYS** set `PGSSLMODE=disable` environment variable
- **VERIFY** database connectivity before proceeding with deployment

### **Rule 3: Docker Permissions**
- **ALWAYS** add user to docker group: `sudo usermod -aG docker $USER`
- **ALWAYS** refresh group membership: `newgrp docker`
- **VERIFY** Docker access before running docker-compose commands
- **NEVER** run Docker commands as root unless absolutely necessary

### **Rule 4: Nginx SSL Configuration**
- **ALWAYS** include SSL certificate paths in Nginx configuration
- **NEVER** configure SSL listeners without certificate files
- **ALWAYS** test Nginx configuration: `sudo nginx -t`
- **INCLUDE** these SSL directives:
  ```nginx
  ssl_certificate /etc/letsencrypt/live/domain/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/domain/privkey.pem;
  include /etc/letsencrypt/options-ssl-nginx.conf;
  ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
  ```

### **Rule 5: Firewall Configuration**
- **ALWAYS** configure iptables for HTTP/HTTPS traffic
- **NEVER** forget to allow SSH (port 22) to maintain access
- **ALWAYS** configure Oracle Cloud Security Lists for ports 80, 443
- **VERIFY** external connectivity after firewall changes

---

## 🐛 **Common Issues & Solutions**

### **Issue 1: Missing Dependencies**
**Problem**: Frontend build fails with missing packages (react-query, react-hot-toast, etc.)
**Solution**: 
```bash
npm install react-query @tanstack/react-query react-hot-toast @tailwindcss/forms
```
**Prevention**: Maintain complete package.json with all dependencies

### **Issue 2: PostgreSQL SSL Errors**
**Problem**: `Permission denied: '/home/ubuntu/.postgresql/postgresql.key'`
**Solution**: 
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vangmayam?sslmode=disable
PGSSLMODE=disable
```
**Prevention**: Always disable SSL for local Docker databases

### **Issue 3: Loguru Logging Errors**
**Problem**: `Invalid compression format: 'gzip'` or `KeyError: '"timestamp"'`
**Solution**: Use simplified logging configuration with `compression="gz"` or `compression=None`
**Prevention**: Test logging configuration in development

### **Issue 4: Docker Permission Denied**
**Problem**: `permission denied while trying to connect to the Docker daemon socket`
**Solution**: 
```bash
sudo usermod -aG docker $USER
newgrp docker
```
**Prevention**: Configure Docker permissions during initial setup

### **Issue 5: Nginx SSL Configuration Errors**
**Problem**: `no "ssl_certificate" is defined for the "listen ... ssl" directive`
**Solution**: Include SSL certificate paths in Nginx configuration before enabling SSL
**Prevention**: Use deployment scripts that handle SSL configuration properly

---

## 📦 **Dependency Management Rules**

### **Backend Dependencies**
- **ALWAYS** include these critical packages in requirements.txt:
  ```
  fastapi>=0.104.0
  uvicorn>=0.24.0
  asyncpg>=0.29.0
  sqlalchemy>=2.0.0
  redis>=5.0.0
  elasticsearch>=8.11.0
  google-cloud-vision>=3.4.0
  PyMuPDF>=1.23.0
  Pillow>=10.0.0
  opencv-python>=4.8.0
  email-validator>=2.0.0
  greenlet>=2.0.0
  aiohttp>=3.8.0
  loguru>=0.7.0
  ```

### **Frontend Dependencies**
- **ALWAYS** include these critical packages in package.json:
  ```json
  {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "react-query": "^3.39.3",
    "@tanstack/react-query": "^4.29.0",
    "react-hot-toast": "^2.4.0",
    "tailwindcss": "^3.3.0",
    "@tailwindcss/forms": "^0.5.0",
    "axios": "^1.4.0",
    "react-router-dom": "^6.3.0"
  }
  ```

---

## 🔒 **Security Rules**

### **Rule 1: Secrets Management**
- **NEVER** commit secrets to Git repository
- **ALWAYS** use environment variables for sensitive data
- **ALWAYS** create .gitignore to exclude credentials
- **ALWAYS** use environment templates (.env.template)

### **Rule 2: SSL/HTTPS**
- **ALWAYS** use HTTPS in production
- **ALWAYS** configure HTTP to HTTPS redirects
- **ALWAYS** use Let's Encrypt for SSL certificates
- **VERIFY** SSL certificate auto-renewal

### **Rule 3: OAuth Configuration**
- **ALWAYS** configure correct redirect URIs in Google Cloud Console
- **ALWAYS** use production domain in OAuth settings
- **VERIFY** OAuth credentials in both backend and frontend

---

## 🏗️ **Architecture Rules**

### **Rule 1: Service Architecture**
- **Backend**: FastAPI with Python 3.11+
- **Frontend**: React with TypeScript
- **Database**: PostgreSQL with asyncpg
- **Cache**: Redis
- **Search**: Elasticsearch
- **Storage**: MinIO (production)
- **Web Server**: Nginx with SSL

### **Rule 2: Container Strategy**
- **USE** Docker Compose for service orchestration
- **ALWAYS** use specific image versions (not :latest)
- **CONFIGURE** proper health checks for all services
- **VERIFY** service dependencies and startup order

### **Rule 3: Monitoring & Logging**
- **IMPLEMENT** structured logging with Loguru
- **CONFIGURE** log rotation and retention
- **MONITOR** service health endpoints
- **TRACK** system resources (disk, memory, CPU)

---

## 🚦 **Deployment Process Rules**

### **Phase 1: Pre-Deployment**
1. **VERIFY** all environment files are complete
2. **TEST** database connectivity
3. **VALIDATE** Docker permissions
4. **CHECK** DNS configuration
5. **CONFIRM** SSL certificate requirements

### **Phase 2: Infrastructure Setup**
1. **CONFIGURE** firewall rules (iptables + Oracle Cloud)
2. **INSTALL** system dependencies
3. **SETUP** Docker and Docker Compose
4. **START** database services
5. **VERIFY** service connectivity

### **Phase 3: Application Deployment**
1. **BUILD** frontend with all dependencies
2. **SETUP** backend with virtual environment
3. **CONFIGURE** Nginx with SSL
4. **START** application services
5. **VERIFY** health endpoints

### **Phase 4: Post-Deployment**
1. **TEST** HTTPS access
2. **VERIFY** API endpoints
3. **CHECK** OAuth functionality
4. **MONITOR** service logs
5. **DOCUMENT** any issues encountered

---

## 📊 **Testing & Validation Rules**

### **Rule 1: Health Checks**
- **ALWAYS** implement `/health` endpoints
- **VERIFY** database connectivity in health checks
- **TEST** all external service dependencies
- **MONITOR** health check response times

### **Rule 2: Integration Testing**
- **TEST** frontend-backend communication
- **VERIFY** OAuth login flow
- **TEST** file upload functionality
- **VALIDATE** search capabilities

### **Rule 3: Performance Testing**
- **MONITOR** response times
- **CHECK** memory usage
- **VERIFY** disk space availability
- **TEST** concurrent user load

---

## 🔧 **Troubleshooting Rules**

### **Rule 1: Systematic Debugging**
1. **CHECK** service logs first: `sudo journalctl -u service-name -f`
2. **VERIFY** environment variables
3. **TEST** individual service connectivity
4. **VALIDATE** configuration files
5. **CHECK** system resources

### **Rule 2: Common Commands**
```bash
# Service management
sudo systemctl status service-name
sudo systemctl restart service-name
sudo journalctl -u service-name -n 50

# Docker debugging
docker-compose ps
docker-compose logs service-name
docker exec -it container-name bash

# Network debugging
curl -I http://localhost:port
netstat -tlnp | grep :port
nslookup domain.com

# SSL debugging
sudo certbot certificates
openssl s_client -connect domain:443
```

### **Rule 3: Error Prioritization**
1. **CRITICAL**: Service won't start (fix immediately)
2. **HIGH**: Security issues (SSL, authentication)
3. **MEDIUM**: Performance issues
4. **LOW**: Cosmetic issues

---

## 📝 **Documentation Rules**

### **Rule 1: Always Document**
- **RECORD** all configuration changes
- **DOCUMENT** troubleshooting steps
- **MAINTAIN** deployment logs
- **UPDATE** environment templates

### **Rule 2: Version Control**
- **COMMIT** configuration changes
- **TAG** stable releases
- **MAINTAIN** clean Git history
- **BACKUP** critical configurations

---

## 🎯 **Success Criteria**

### **Deployment is Successful When:**
- ✅ All services are running and healthy
- ✅ HTTPS access works correctly
- ✅ API endpoints respond with 200 status
- ✅ Frontend loads without errors
- ✅ OAuth authentication functions
- ✅ Database operations work
- ✅ Search functionality is operational
- ✅ SSL certificates are valid and auto-renewing

### **Deployment is Failed When:**
- ❌ Any service fails to start
- ❌ Health checks return errors
- ❌ SSL configuration is broken
- ❌ Database connectivity issues
- ❌ Frontend build failures
- ❌ Missing critical dependencies

---

## 🔄 **Maintenance Rules**

### **Regular Maintenance Tasks**
- **WEEKLY**: Check service logs for errors
- **MONTHLY**: Verify SSL certificate status
- **QUARTERLY**: Update dependencies
- **ANNUALLY**: Review and update security configurations

### **Emergency Procedures**
- **SERVICE DOWN**: Check logs, restart service, verify dependencies
- **SSL EXPIRED**: Renew certificate, update Nginx configuration
- **DISK FULL**: Clean logs, remove old files, expand storage
- **HIGH LOAD**: Check resource usage, optimize queries, scale services

---

## 📚 **Reference Links**

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **React Documentation**: https://react.dev/
- **Docker Compose**: https://docs.docker.com/compose/
- **Nginx SSL Configuration**: https://nginx.org/en/docs/http/configuring_https_servers.html
- **Let's Encrypt**: https://letsencrypt.org/docs/
- **Oracle Cloud Networking**: https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/overview.htm

---

**Last Updated**: 2025-01-29  
**Version**: 1.0  
**Status**: Production Ready

---

*This document should be updated whenever new deployment challenges are encountered and resolved.*
