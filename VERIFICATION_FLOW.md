# How User Verification & Permission System Works

## 1. **User Verification Flow** (Discord Bot Side)

### Step 1: User initiates verification via Discord
```
User runs: /verify <roblox_username>
```

### Step 2: Discord Bot verifies Roblox account exists
```python
# discord_bot.py - verify_account()
user_id = await roblox.get_user_id(roblox_username)
if not user_id:
    return "Roblox user not found"
```

### Step 3: Bot generates verification code
```python
# security_manager.py
code = security.generate_verification_code()
# Example: "ABC123XYZ789"
```

### Step 4: User adds code to Roblox bio
- Discord bot DMs user the code
- User adds it to their Roblox profile bio
- Bot automatically checks bio for the code

### Step 5: Account is linked
```python
# database.py - link_discord_to_roblox()
discord_users.update_one({
    "discord_id": user_discord_id,
    "roblox_user_id": roblox_user_id,
    "roblox_username": roblox_username
})
```

---

## 2. **How the Roblox Bot Knows User Is Verified** (In-Game)

### When trade request comes in:

```
Player (DignityBot2000) initiates trade with bot
```

### Bot gets username and converts to UserID:
```lua
-- ps99lua_working.lua
tradeUser = players:GetUserIdFromNameAsync(username)
-- Example: tradeUser = 9779977974
```

### Bot sends HTTP request to backend:
```lua
request({
    Url = website .. "/check",
    Method = "POST",
    Body = httpService:JSONEncode({
        ["userId"] = tradeUser,
        ["game"] = "PS99"
    }),
    Headers = {
        ["Authorization"] = auth
    }
})
```

### Backend API checks if user is verified:
```python
# api.py - /check endpoint
@app.post("/check")
async def check_user_status(request: CheckRequest):
    # 1. Look up Discord user linked to this Roblox ID
    discord_user = await db.get_discord_user_by_roblox_id(request.userId)
    
    if not discord_user:
        return {"method": "USERNOTFOUND"}  # User not registered
    
    # 2. User is verified! Check their inventory/pending requests
    # ...
```

---

## 3. **How Bot Knows Which Pets You Can Deposit**

### Deposits: Default mode (anyone verified can deposit)
```python
# trade_processor.py - validate_deposit()
SUPPORTED_PETS = {
    "Huge Dragon",
    "Titanic Dragon", 
    "Huge Turtle",
    "Titanic Turtle",
    # ... all huge/titanic pets
}

# Check if deposited pets are in supported list
for pet in deposited_pets:
    if pet not in SUPPORTED_PETS:
        return error("Please deposit only Huge/Titanic pets")
```

### Deposits: Gem limits
```python
MIN_GEM_DEPOSIT = 50_000_000  # 50M
MAX_GEM_DEPOSIT = 10_000_000_000  # 10B

if gems < MIN_GEM_DEPOSIT:
    return error(f"Minimum is {MIN_GEM_DEPOSIT:,}")
if gems > MAX_GEM_DEPOSIT:
    return error(f"Maximum is {MAX_GEM_DEPOSIT:,}")
if gems % 50_000_000 != 0:
    return error("Must be multiple of 50M")
```

---

## 4. **How Bot Knows What You Can Withdraw**

### Withdrawals: Only when Discord user requests
```python
# discord_bot.py - withdraw command
@bot.tree.command(name="withdraw")
async def withdraw_pets(interaction: discord.Interaction, pet_name: str):
    # 1. Check if user is verified (linked to Roblox account)
    discord_user = await db.get_discord_user(interaction.user.id)
    if not discord_user:
        return "You must verify first!"
    
    # 2. Get their inventory in Discord storage
    inventory = await db.get_user_inventory(interaction.user.id)
    
    # 3. Check if they have that pet
    if pet_name not in inventory:
        return "You don't have that pet!"
    
    # 4. Mark as pending withdrawal
    await db.set_pending_withdrawal(
        discord_id=interaction.user.id,
        roblox_user_id=discord_user['roblox_user_id'],
        pets=[pet_name]
    )
```

### When Roblox bot checks for withdrawal:
```python
# api.py - when checking if withdrawal pending
pending = await db.get_pending_withdrawal(roblox_user_id)
if pending:
    return {
        "method": "Withdraw",
        "pets": pending['pets']  # ["Shiny Golden Dragon", ...]
    }
```

---

## 5. **Complete Trade Verification Chain**

```
┌─────────────────────────────────────────────────────┐
│  1. Trade Request (Player joins bot in-game)        │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  2. Roblox Bot converts username to UserID          │
│     (DignityBot2000 → 9779977974)                   │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  3. Backend /check endpoint                         │
│     Query: Is this Roblox ID linked to Discord?     │
└─────────────────────────────────────────────────────┘
                          ↓
         ┌───────────────────────────────┐
         │                               │
        NO                              YES
         │                               │
         ↓                               ↓
    Return                    Check for pending
    USERNOTFOUND            withdrawal request
         │                               │
         ↓                               ↓
    Reject trade            ┌──────────────────┐
                             │                  │
                            YES              NO
                             │                │
                             ↓                ↓
                         Return          Return
                      "Withdraw"       "Deposit"
                      + pet list         (default)
                             │                │
                             └────────┬───────┘
                                      ↓
                        ┌──────────────────────┐
                        │  Validate trade      │
                        │  Check pet type      │
                        │  Check gem amounts   │
                        └──────────────────────┘
                                      ↓
                        ┌──────────────────────┐
                        │  Complete trade      │
                        │  Update inventory    │
                        │  Log transaction     │
                        └──────────────────────┘
```

---

## 6. **Key Database Collections**

```javascript
// Discord Users (Verification Link)
{
    discord_id: 123456789,
    roblox_user_id: 9779977974,
    roblox_username: "DignityBot2000",
    verified: true,
    verified_at: ISODate("2024-01-29"),
    status: "active"
}

// User Inventory (Deposited pets)
{
    discord_id: 123456789,
    game: "PS99",
    pets: {
        "Shiny Dragon": 2,
        "Golden Turtle": 1,
        "Rainbow Phoenix": 3
    },
    gems: 500_000_000,
    last_updated: ISODate("2024-01-29")
}

// Pending Withdrawals
{
    discord_id: 123456789,
    roblox_user_id: 9779977974,
    pets: ["Shiny Dragon", "Rainbow Turtle"],
    requested_at: ISODate("2024-01-29"),
    status: "pending"
}

// Transactions (Audit log)
{
    discord_id: 123456789,
    type: "deposit",
    pets: ["Shiny Dragon"],
    gems: 1000000,
    completed_at: ISODate("2024-01-29"),
    status: "completed"
}
```

---

## Summary

1. **Verification**: User links Discord ↔ Roblox via `/verify` command + code in bio
2. **Deposits**: Verified users can deposit Huge/Titanic pets (50M-10B gems) anytime
3. **Withdrawals**: Only pets that user previously deposited (stored in inventory)
4. **Permissions**: Controlled via Discord commands (Discord user decides withdrawal)
5. **Validation**: Backend validates pets, gems, and user status on every trade
