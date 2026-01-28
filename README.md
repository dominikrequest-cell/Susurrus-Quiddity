# 🎮 Roblox Pet Trading Discord Bot

A complete system for automated Roblox pet and gem trading directly through Discord. Users verify their Roblox account, deposit pets/gems through in-game trades, and manage inventory via Discord commands.

## 📋 Architecture Overview

```
Discord User
    ↓
Discord Bot (Python) ─→ FastAPI Backend (Python/Render)
    ↓                         ↓
User Database          MongoDB Database
    ↓
Roblox Game (Lua)  ←→ API (Verify Trades) → Database (Record Transactions)
```

## 🔧 Core Components

### 1. **Discord Bot** (`discord_bot.py`)
- Account verification with Roblox
- Inventory management
- Deposit/Withdrawal initiation
- Transaction history
- Built with `discord.py`

### 2. **FastAPI Backend** (`api.py`)
- Trade validation and processing
- Secure payload signing for Lua
- Inventory tracking
- Transaction recording
- Pet value management

### 3. **Roblox Lua Script** (`ps99lua.lua`)
- Detects completed trades
- Identifies pets and gem amounts
- Sends secure trade data to API
- Displays messages to users

### 4. **Database** (`database.py`)
- MongoDB for scalability
- User linking (Discord ↔ Roblox)
- Inventory tracking
- Transaction history
- Pet values/prices

### 5. **Security** (`security_manager.py`)
- Verification code generation
- Payload signing (HMAC-SHA256)
- Replay attack prevention
- Username validation

### 6. **Roblox API Integration** (`roblox_verification.py`)
- User lookup and caching
- Bio verification for ownership
- Thumbnail fetching

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- MongoDB (local or Atlas)
- Discord Bot Token
- Docker (optional)

### Setup

1. **Clone and Install**
```bash
git clone <repo>
cd Susurrus-Quiddity
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your credentials:
# - DISCORD_TOKEN: Your Discord bot token
# - MONGODB_URL: MongoDB connection string
# - API_SECRET: Random secret key for signing
```

3. **Run Locally**

```bash
# Terminal 1: API Server
python -m uvicorn api:app --reload

# Terminal 2: Discord Bot
python discord_bot.py
```

4. **Or with Docker**
```bash
docker-compose up
```

## 📖 Usage

### User Flow

#### 1. Verify Roblox Account
```
Discord: !verify YourRobloxUsername
Bot: Generates code → User adds to Roblox bio → !verify-confirm YourRobloxUsername
```

#### 2. Deposit Pets/Gems
```
Discord: !deposit
User: Joins Roblox game → Trades bot
Lua Script: Detects trade → Sends to API
API: Validates → Updates Discord inventory
```

#### 3. Withdraw Pets
```
Discord: !withdraw
API: Gets user's inventory
Lua Script: Sends requested pets
User: Accepts trade in game
```

#### 4. Check Inventory
```
Discord: !inventory
Shows: All pets, quantities, gem balance
```

## 🔐 Security Features

### Verification Code System (from PHP)
- 16-word random code generation
- User puts code in Roblox bio
- Bot verifies ownership before linking

### Payload Signing
- HMAC-SHA256 signing for all trades
- Timestamp validation (5-minute window)
- Replay attack prevention
- Secure comparison (timing-safe)

### Username Validation
- Format checking (alphanumeric + underscore)
- Length validation (3-20 chars)
- Single underscore max

## 📊 Database Schema

### Users Collection
```javascript
{
  user_id: 12345,
  username: "PlayerName",
  description: "Roblox bio content",
  thumbnail: "https://...",
  updated_at: Date
}
```

### Discord Users Collection
```javascript
{
  discord_id: 123456789,
  roblox_user_id: 12345,
  discord_username: "user#1234",
  verified: true,
  gem_balance: 1000000000,
  verified_at: Date
}
```

### Inventory Collection
```javascript
{
  discord_id: 123456789,
  pet_name: "Shiny Golden Huge Bat",
  quantity: 5,
  pet_data: {rarity: "Golden", shiny: true},
  updated_at: Date
}
```

### Transactions Collection
```javascript
{
  type: "deposit",
  discord_id: 123456789,
  roblox_user_id: 12345,
  pets: [{name: "...", rarity: "...", shiny: bool}],
  gems: 500000000,
  status: "completed",
  total_value: 5000,
  created_at: Date
}
```

## API Endpoints

### Verification
- `POST /verify/start` - Generate verification code
- `POST /verify/confirm` - Confirm Roblox account ownership

### Trading
- `POST /deposit/check` - Validate deposit before trade
- `POST /deposit/complete` - Record completed deposit
- `POST /withdraw/check` - Get user's inventory for withdrawal
- `POST /withdraw/complete` - Record completed withdrawal

### Inventory
- `GET /items/all` - Get all supported items and values
- `GET /user/{discord_id}/inventory` - Get user's inventory
- `GET /user/{discord_id}/transactions` - Get transaction history

### Health
- `GET /health` - Service health check

## 🎮 Roblox Integration

### Lua Script Responsibilities
1. **Trade Detection**
   - Monitor trading window for completion
   - Extract pets (name, rarity, shiny status)
   - Extract gem amount

2. **Secure Communication**
   - Sign payloads with API secret
   - Include timestamp to prevent replays
   - Verify response signatures

3. **User Messaging**
   - Confirmation messages
   - Error handling
   - Trade status updates

### Trade Flow (Lua ↔ API)

```lua
-- 1. Check if user wants to deposit/withdraw
GET /withdraw/check?userId=12345
← {method: "Deposit"/"Withdraw", pets: [...], gems: N}

-- 2. User completes trade in game
-- (Lua detects via TradeWindow)

-- 3. Send completed trade data
POST /deposit/complete
{
  userId: 12345,
  pets: [{name: "...", rarity: "...", shiny: true}],
  gems: 500000000,
  signature: "HMAC-SHA256-HASH",
  timestamp: 1704067200
}
← {success: true, transactionId: "..."}
```

## 💾 Pet Values

Pet values are maintained in MongoDB and scraped from pet value sites:

```python
# values.py handles scraping
# Updates pet values periodically
# Values used for inventory display and trade records
```

## 🌐 Deployment

### Option 1: Docker Compose (Recommended)
```bash
docker-compose up -d
```

### Option 2: Render.com (For Backend)
```bash
# Create new Web Service
# Connect GitHub repo
# Set environment variables in Render dashboard
# Deploy!
```

### Option 3: Heroku/AWS
```bash
# Similar process - set environment, push code
```

## 🛡️ Production Checklist

- [ ] Change API_SECRET to random strong key
- [ ] Use MongoDB Atlas (managed database)
- [ ] Enable HTTPS for API
- [ ] Set up Discord bot scopes: `bot`, `applications.commands`
- [ ] Test deposit/withdraw flow
- [ ] Monitor error logs
- [ ] Set up alerts for failed trades
- [ ] Rate limiting on API endpoints
- [ ] Database backups

## 🐛 Troubleshooting

### Bot Won't Start
```bash
# Check Discord token
echo $DISCORD_TOKEN

# Verify MongoDB connection
python -c "from database import Database; db = Database(); print('OK')"
```

### Trades Not Recording
```bash
# Check API logs
tail -f logs/api.log

# Verify Lua signature
# Check timestamp not too old
```

### Inventory Not Updating
```bash
# Check transaction status in MongoDB
db.transactions.find({status: "completed"})

# Verify inventory operation
db.inventory.find({discord_id: YOUR_ID})
```

## 📚 Additional Resources

- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Roblox API Docs](https://developer.roblox.com/)
- [MongoDB Python Driver](https://pymongo.readthedocs.io/)

## 📝 Notes

- Pets have static values (from scraper)
- Gems are raw currency (no value)
- All trades are permanent once completed
- Transactions are immutable audit trail
- Security codes expire after 10 minutes

## 🔄 Future Enhancements

- [ ] Slash commands for Discord
- [ ] Pet marketplace
- [ ] Trading between users
- [ ] Admin control panel
- [ ] Webhook notifications
- [ ] Rate limiting
- [ ] Email notifications
- [ ] Backup system

## 📧 Support

For issues, see GitHub Issues or contact support in Discord server.

---

**Made with ❤️ for the Pet Simulator community**
