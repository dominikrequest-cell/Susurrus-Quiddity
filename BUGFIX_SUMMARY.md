# Trading Bot Bug Fix - Endpoint URLs Corrected

## Problem Identified
The Roblox Lua trading bot was failing with "Server connection error - try again later" when attempting to check pending trades. The error occurred at this point in the logs:
```
12:40:12 -- [Trade Bot] Failed to check pending trades with server
```

## Root Cause
The Lua script was calling **incorrect API endpoints** that don't exist in the FastAPI backend:

### Incorrect Endpoints (OLD):
1. `POST /trading/items/check-pending` ❌
2. `POST /trading/items/confirm-ps99-deposit` ❌
3. `POST /trading/items/confirm-withdraw` ❌

These endpoints don't exist in `api.py`, causing the HTTP requests to fail with `404 Not Found` errors.

## Solution Applied
Updated all three endpoint URLs in `ps99lua_working.lua` to match the actual API endpoints:

### Corrected Endpoints (NEW):
1. **Line 642**: `POST /withdraw/check` ✅
   - Purpose: Check what items user wants to withdraw
   - Parameters: `userId`, `game`
   - Response: Returns user's inventory or `method: "USER_NOT_FOUND"`

2. **Line 505**: `POST /deposit/complete` ✅
   - Purpose: Complete a deposit transaction
   - Parameters: `userId`, `pets`, `gems`, `game`
   - Response: Returns transaction ID and success message

3. **Line 527**: `POST /withdraw/complete` ✅
   - Purpose: Complete a withdrawal transaction
   - Parameters: `userId`, `pets`, `gems`, `game`
   - Response: Returns transaction ID and success message

## Changes Made

### File: `ps99lua_working.lua`

**Change 1** (Line 642):
```lua
-- OLD
Url = website .. "/trading/items/check-pending"
Body = httpService:JSONEncode({
    ["userId"] = tradeUser,
    ["authKey"] = auth,      -- ← Wrong parameter name
    ["game"] = "PS99"
})

-- NEW
Url = website .. "/withdraw/check"
Body = httpService:JSONEncode({
    ["userId"] = tradeUser,
    ["game"] = "PS99"
})
```

**Change 2** (Line 505):
```lua
-- OLD
Url = website.."/trading/items/confirm-ps99-deposit"
Body = httpService:JSONEncode({
    ["userId"] = tradeUser,
    ["items"] = tradingItems,
    ["authKey"] = auth,      -- ← Wrong parameter name
    ["game"] = "PS99"
})

-- NEW
Url = website.."/deposit/complete"
Body = httpService:JSONEncode({
    ["userId"] = tradeUser,
    ["pets"] = tradingItems,  -- ← Matches API schema
    ["gems"] = 0,
    ["game"] = "PS99"
})
```

**Change 3** (Line 527):
```lua
-- OLD
Url = website .."/trading/items/confirm-withdraw"
Body = httpService:JSONEncode({
    ["userId"] = tradeUser,
    ["authKey"] = auth
})

-- NEW
Url = website .."/withdraw/complete"
Body = httpService:JSONEncode({
    ["userId"] = tradeUser,
    ["pets"] = tradingItems,
    ["gems"] = 0,
    ["game"] = "PS99"
})
```

## Verification
All endpoint URLs now match the documented API in `api.py`:
- ✅ `/withdraw/check` - Line 177
- ✅ `/deposit/complete` - Line 119
- ✅ `/withdraw/complete` - Line 169

## Expected Outcome
After deploying the updated `ps99lua_working.lua` script:
1. Trade request checks will succeed ✅
2. No more "Failed to check pending trades with server" errors
3. Deposits and withdrawals will complete successfully
4. Server will receive complete trade data with correct parameter names

## Testing Recommendations
1. Deploy the updated Lua script to the Roblox game
2. Initiate a test trade with the bot
3. Verify that:
   - Trade requests are recognized
   - Deposits process without errors
   - Withdrawals process without errors
   - Transaction confirmation messages appear in chat
