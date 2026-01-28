"""
Complete deployment guide for the Pet Trading Bot system
Includes setup for local development, staging, and production
"""

# ============= PROJECT STRUCTURE =============

Susurrus-Quiddity/
├── discord_bot.py              # Discord bot main file
├── api.py                       # FastAPI backend
├── database.py                  # MongoDB database layer
├── roblox_verification.py       # Roblox API integration
├── trade_processor.py           # Trade validation & processing
├── security_manager.py          # Payload signing & verification
├── config.py                    # Configuration management
├── ps99lua.lua                  # Roblox Lua script
├── lua_integration.lua          # Lua helper functions
├── values.py                    # Pet value scraper
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── docker-compose.yml           # Docker orchestration
├── Dockerfile.api               # API container
├── Dockerfile.bot               # Bot container
├── README.md                    # Main documentation
├── LUA_INTEGRATION.md           # Lua integration guide
├── DEPLOYMENT.md                # This file
├── login.php                    # Reference (legacy)
├── roblox_handler.php          # Reference (legacy)


# ============= LOCAL DEVELOPMENT SETUP =============

## Step 1: Clone Repository
git clone <repo>
cd Susurrus-Quiddity

## Step 2: Create Virtual Environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

## Step 3: Install Dependencies
pip install -r requirements.txt

## Step 4: Setup MongoDB
# Option A: Local MongoDB
# Download and run MongoDB Community Edition
# Or use: brew install mongodb-community (macOS)

# Option B: MongoDB Atlas (Cloud)
# Create account at mongodb.com/cloud
# Create cluster and get connection string

## Step 5: Configure Environment
cp .env.example .env
# Edit .env with:
# - DISCORD_TOKEN from Discord Developer Portal
# - MONGODB_URL from MongoDB Atlas
# - Random API_SECRET

## Step 6: Discord Bot Setup
# 1. Go to https://discord.com/developers/applications
# 2. Create New Application
# 3. Go to "Bot" section → Add Bot
# 4. Copy token to DISCORD_TOKEN in .env
# 5. Enable intents:
#    - Message Content Intent
#    - Guild Members Intent
# 6. Go to OAuth2 → URL Generator
# 7. Select scopes: bot
# 8. Select permissions: Send Messages, Read Message History, Embed Links
# 9. Copy generated URL and invite bot to server

## Step 7: Run Services

# Terminal 1: MongoDB (if local)
mongod

# Terminal 2: API Server
python -m uvicorn api:app --reload --port 8000

# Terminal 3: Discord Bot
python discord_bot.py

## Step 8: Test
# In Discord: !verify <username>
# Check console for logs


# ============= DOCKER SETUP (Recommended) =============

## Prerequisites
# - Docker installed
# - Docker Compose installed

## Step 1: Build Images
docker-compose build

## Step 2: Configure Environment
cp .env.example .env
# Edit .env with your credentials

## Step 3: Start Services
docker-compose up -d

## Step 4: Check Logs
docker-compose logs -f api
docker-compose logs -f bot

## Step 5: Stop Services
docker-compose down

## Useful Commands
# View running containers
docker-compose ps

# Execute command in container
docker-compose exec api python -c "from database import Database; db = Database(); print('OK')"

# Rebuild after code changes
docker-compose up -d --build

# Clean everything
docker-compose down -v


# ============= PRODUCTION DEPLOYMENT (Render.com) =============

## Prerequisites
# - GitHub account with repo
# - Render.com account
# - MongoDB Atlas cluster (recommended)

## Step 1: Push to GitHub
git add .
git commit -m "Deploy to Render"
git push origin main

## Step 2: Create API Service on Render

### In Render Dashboard:
1. New → Web Service
2. Connect GitHub repo
3. Select Susurrus-Quiddity repo
4. Set name: "pet-trading-api"
5. Environment: Python 3.11
6. Build Command: pip install -r requirements.txt
7. Start Command: uvicorn api:app --host 0.0.0.0 --port 8000
8. Set Environment Variables:
   - MONGODB_URL: Your MongoDB Atlas connection string
   - API_SECRET: Random secure string (at least 32 characters)
   - LOG_LEVEL: INFO
9. Set Plan: Paid (optional: Starter = free)
10. Deploy!

## Step 3: Create Discord Bot Service on Render

1. New → Background Worker
2. Connect same repo
3. Set name: "pet-trading-bot"
4. Environment: Python 3.11
5. Build Command: pip install -r requirements.txt
6. Start Command: python discord_bot.py
7. Set Environment Variables:
   - DISCORD_TOKEN: Your Discord bot token
   - MONGODB_URL: Same as API
   - API_SECRET: Same as API
   - API_URL: Your Render API URL (https://pet-trading-api.onrender.com)
   - LOG_LEVEL: INFO
8. Deploy!

## Step 4: Update DNS/Webhooks
# Your API is now at: https://pet-trading-api.onrender.com
# Update Lua script to use this URL

## Step 5: Monitor
# Render Dashboard → Service → Logs
# Check for errors and warnings


# ============= PRODUCTION DEPLOYMENT (AWS) =============

## Step 1: Prepare Code
# Ensure .env is NOT in git
# Add .env to .gitignore

## Step 2: Create RDS Database
# AWS Console → RDS
# Create MongoDB cluster or use Atlas

## Step 3: Create EC2 Instance
# Ubuntu 22.04
# t3.medium or larger
# Open ports: 22 (SSH), 8000 (API)

## Step 4: Deploy to EC2
ssh -i key.pem ubuntu@instance-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repo
git clone <repo>
cd Susurrus-Quiddity

# Configure .env
nano .env  # Add your configuration

# Start services
docker-compose up -d

## Step 5: Setup Nginx (Reverse Proxy)
# Install Nginx
sudo apt-get install nginx

# Configure /etc/nginx/sites-available/default
upstream api {
    server localhost:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Restart Nginx
sudo systemctl restart nginx

## Step 6: SSL Certificate (Let's Encrypt)
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com


# ============= PRODUCTION DEPLOYMENT (GCP/Azure) =============

# Similar process to AWS
# Use Google Cloud Run or Azure Container Instances
# Configure cloud SQL for database
# Set environment variables in cloud console


# ============= DATABASE BACKUP & MIGRATION =============

## Backup MongoDB Atlas
# Enable automated backups in Atlas console
# Or use mongodump:
mongodump --uri="mongodb+srv://..." --out=backup_folder

## Restore MongoDB
mongorestore --uri="mongodb+srv://..." backup_folder

## Export/Import Data
# Export
mongoexport --uri="mongodb+srv://..." --collection=users --out=users.json

# Import
mongoimport --uri="mongodb+srv://..." --collection=users < users.json


# ============= MONITORING & LOGGING =============

## Application Logs
# Check container logs
docker-compose logs api
docker-compose logs bot

# Or use logging service
# CloudWatch (AWS)
# Stackdriver (GCP)
# Azure Monitor (Azure)

## Database Monitoring
# MongoDB Atlas → Monitoring tab
# Check connection stats, query performance

## Uptime Monitoring
# Use Uptime Robot or similar
# Monitor: https://api.yourdomain.com/health

## Error Tracking
# Consider using Sentry
# pip install sentry-sdk
# Configure in config.py


# ============= SCALING CONSIDERATIONS =============

## Horizontal Scaling
# Run multiple API instances behind load balancer
# MongoDB connection pooling
# Redis for caching verification codes

## Database Optimization
# Index frequently queried fields
# Archive old transactions
# Optimize query patterns

## Rate Limiting
# Add rate limiting middleware in FastAPI
# Prevent abuse from bots

## Caching
# Redis for verification codes (TTL)
# Cache pet values
# Cache user data


# ============= SECURITY CHECKLIST =============

- [ ] API_SECRET changed from default
- [ ] HTTPS enabled (SSL certificate)
- [ ] Environment variables not in git
- [ ] Database credentials in .env
- [ ] Discord token not exposed
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (using ORM)
- [ ] XSS prevention in Discord bot
- [ ] Regular security audits
- [ ] Backup and disaster recovery plan
- [ ] Database encryption at rest
- [ ] Regular dependency updates


# ============= TROUBLESHOOTING =============

## API Won't Start
# Check Python version
python --version  # Should be 3.11+

# Check port not in use
lsof -i :8000

# Check MongoDB connection
python -c "from database import Database; db = Database(); print('OK')"

## Discord Bot Issues
# Verify token
echo $DISCORD_TOKEN

# Check intents enabled in Discord Developer Portal
# Message Content Intent required!

# Test connection
python -c "import discord; print(discord.__version__)"

## Trades Not Recording
# Check API logs
curl https://api.yourdomain.com/health

# Verify MongoDB collections
db.transactions.find({}).limit(5)

# Check Lua console in Roblox
# Look for request responses


# ============= UPGRADE & MAINTENANCE =============

## Update Dependencies
pip install --upgrade -r requirements.txt
docker-compose up -d --build

## Blue-Green Deployment
# Run new version in parallel
# Switch traffic gradually
# Rollback if needed

## Database Migrations
# Use MongoDB version compatibility
# Test on staging first
# Plan downtime if needed

## Feature Flags
# Add feature switches
# Deploy code before feature is live
# Gradual rollout to users


# ============= SUPPORT & DOCUMENTATION =============

API Documentation: https://api.yourdomain.com/docs
GitHub Issues: https://github.com/owner/repo/issues
Discord Server: [link]

