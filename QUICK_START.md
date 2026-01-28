"""
Quick Start Testing Guide
Get the bot running and test the full flow in < 30 minutes
"""

# ============= 5-MINUTE LOCAL SETUP =============

## 1. Install & Configure (5 min)
```bash
# Install Python 3.11+
python --version  # Should be 3.11+

# Clone and enter
cd Susurrus-Quiddity

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment
cp .env.example .env
```

## 2. Get Discord Token (3 min)
```
1. Go: https://discord.com/developers/applications
2. New Application
3. Bot section → Add Bot
4. Copy token
5. Paste in .env as DISCORD_TOKEN
6. Enable: Message Content Intent
7. OAuth2 → URL Generator → bot → Copy URL → Invite to server
```

## 3. MongoDB Setup (2 min)
```
Option A - Local:
  mongod  # Run in another terminal

Option B - Atlas (recommended):
  1. https://www.mongodb.com/cloud/atlas
  2. Create account
  3. Create cluster (free tier)
  4. Get connection string
  5. Paste in .env as MONGODB_URL
```

## 4. Run Services
```bash
# Terminal 1: API Server
python -m uvicorn api:app --reload

# Terminal 2: Discord Bot (in same venv)
python discord_bot.py

# Monitor both for "ready" messages
```


# ============= TESTING THE FLOW =============

## Test 1: Bot Startup
```
Expected in Terminal 2:
  "🤖 [YourBotName] is ready!"
  
Check Discord:
  Bot should appear in member list
```

## Test 2: Help Command
```
Discord: !help
Expected: Embed with all commands
```

## Test 3: Verification Flow (10 min)
```bash
## In Discord:
!verify YourRobloxUsername

# Expected: DM with code (e.g., "monday friday caramel...")

# NOW GO PUT CODE IN ROBLOX BIO:
# 1. Visit: https://roblox.com/users/[ID]/profile
# 2. About section → Edit
# 3. Paste the code
# 4. Save

# Back to Discord:
!verify-confirm YourRobloxUsername

# Expected: ✅ Success message
```

## Test 4: Inventory (Should be empty)
```
Discord: !inventory
Expected: "You don't have any pets yet"
```

## Test 5: Check Balance
```
Discord: !balance
Expected: 0 gems
```

## Test 6: API Health Check
```bash
curl http://localhost:8000/health

Expected:
{
  "status": "ok",
  "timestamp": "2024-01-28T..."
}
```

## Test 7: Get Supported Items
```bash
curl http://localhost:8000/items/all

Expected:
{
  "items": [],  # Empty initially
  "values": {},
  "timestamp": "..."
}
```


# ============= MANUAL INVENTORY TEST =============

## Add Pet Manually (for testing)
```bash
python

from database import Database
import asyncio

async def test():
    db = Database()
    your_discord_id = 123456789  # Your Discord ID
    
    # Add a test pet
    await db.add_pet_to_inventory(
        your_discord_id,
        "Shiny Golden Huge Bat",
        quantity=1
    )
    
    # Check inventory
    inv = await db.get_inventory(your_discord_id)
    print(inv)

asyncio.run(test())
```

## Now Check in Discord
```
Discord: !inventory
Expected: "Shiny Golden Huge Bat - Quantity: 1"
```


# ============= DEPOSIT FLOW TEST (Simulated) =============

## Simulate Deposit (without Roblox game)
```bash
python

import asyncio
from database import Database
from trade_processor import TradeProcessor, TradeData, TradeType, TradeItem
from security_manager import SecurityManager

async def test_deposit():
    db = Database()
    security = SecurityManager(api_secret="test-secret")
    processor = TradeProcessor(db, security)
    
    # First, link Discord user to Roblox
    your_discord_id = 123456789
    test_roblox_id = 987654321
    
    await db.link_discord_to_roblox(
        your_discord_id,
        test_roblox_id,
        "YourDiscordName"
    )
    
    # Create deposit trade
    pets = [
        TradeItem(
            name="Huge Bat",
            rarity="Golden",
            shiny=True,
            quantity=1
        )
    ]
    
    trade = TradeData(
        type=TradeType.DEPOSIT,
        user_id=test_roblox_id,
        pets=pets,
        gems=50_000_000  # 50M gems
    )
    
    # Process deposit
    result = await processor.process_deposit(
        your_discord_id,
        test_roblox_id,
        trade
    )
    
    print("Deposit result:", result)
    
    # Check inventory in Discord
    inv = await db.get_inventory(your_discord_id)
    print("Inventory:", inv)
    
    # Check gems
    gems = await db.get_user_gem_balance(your_discord_id)
    print("Gems:", gems)

asyncio.run(test_deposit())
```

## In Discord
```
!inventory
Expected: 
  Shiny Golden Huge Bat - 1
  💎 Gems: 50,000,000
```


# ============= API ENDPOINT TESTS =============

## Test Health
```bash
curl http://localhost:8000/health
```

## Test Get Items
```bash
curl http://localhost:8000/items/all
```

## Test Verify Start (Invalid User)
```bash
curl -X POST http://localhost:8000/verify/start \
  -H "Content-Type: application/json" \
  -d '{"robloxUsername": "InvalidUser123NotReal"}'

Expected: 404 error
```

## Test Verify Start (Valid User)
```bash
curl -X POST http://localhost:8000/verify/start \
  -H "Content-Type: application/json" \
  -d '{"robloxUsername": "ROBLOX"}'  # Famous ROBLOX user

Expected: 200 with code in response
```


# ============= DOCKER TEST =============

## Run with Docker Compose
```bash
docker-compose up

# Wait for all services to start
# Should see:
# - MongoDB running
# - API server listening on 8000
# - Discord bot ready message
```

## Test in Docker
```bash
# API health
curl http://localhost:8000/health

# Discord commands from Discord app
!help
!verify YourUsername
```

## Stop Docker
```bash
docker-compose down
```


# ============= COMMON ISSUES & FIXES =============

### "ModuleNotFoundError: No module named 'discord'"
```bash
# Make sure venv is activated
source venv/bin/activate
# Then reinstall
pip install -r requirements.txt
```

### "DISCORD_TOKEN not set"
```bash
# Check .env file exists and has token
cat .env | grep DISCORD_TOKEN
# If empty, get from Discord Developer Portal
```

### "Cannot connect to MongoDB"
```bash
# Check MongoDB running
mongod --version  # Should print version

# Or use MongoDB Atlas URL in .env
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/...
```

### "Bot won't respond to commands"
```bash
# Check Message Content Intent is enabled
# Discord Developer Portal → Bot → Intents → Message Content Intent

# Check bot has permission in server
# Server Settings → Roles → @BotRole → Message Permissions
```

### "Verify returns 'user not found'"
```bash
# Make sure Roblox username is correct (case-sensitive)
# Try with famous account: ROBLOX
# Check Roblox API is accessible: curl https://users.roblox.com/v1/users/1
```

### "Port 8000 already in use"
```bash
# Find process using port
lsof -i :8000

# Kill it or use different port
python -m uvicorn api:app --port 8001
```

### "MongoDB authentication failed"
```bash
# Check username/password in connection string
# MongoDB Atlas: Whitelist your IP
# Local MongoDB: Make sure mongod is running
```


# ============= MONITORING =============

## Check API Logs
```bash
# In terminal running API
# Should see GET/POST requests logged
# Errors will show with 500 status
```

## Check Bot Logs
```bash
# In terminal running bot
# Check for command messages
# Errors will print with traceback
```

## MongoDB Monitoring
```bash
mongosh  # or mongosh if installed

use pet_trading_bot
db.discord_users.find()  # See linked accounts
db.transactions.find()  # See all trades
db.inventory.find()  # See all inventories
```

## Docker Logs
```bash
docker-compose logs api -f  # Follow API logs
docker-compose logs bot -f  # Follow bot logs
docker-compose logs mongodb -f  # Follow DB logs
```


# ============= NEXT STEPS =============

After testing locally:

1. Deploy to production (see DEPLOYMENT.md)
2. Update Lua script with API URL (see LUA_INTEGRATION.md)
3. Test with Roblox bot account
4. Enable for real users gradually
5. Monitor errors and optimize

---

**Total testing time: 30-45 minutes**

You should have:
- ✅ Bot responding to commands
- ✅ Verification flow working
- ✅ Inventory tracking
- ✅ API responding
- ✅ Database connected

