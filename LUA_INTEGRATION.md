Cannot be blank"""
Integration guide for connecting the Lua script to the Python backend
This shows how ps99lua.lua should be updated to use the new API
"""

# UPDATED ps99lua.lua INTEGRATION

# At the top of ps99lua.lua, update the API endpoint:

local website = os.getenv("API_URL") or "https://api.bloxyspin.org"  # Change to your API URL
local auth = os.getenv("API_SECRET") or "SEXILOVE2024SGWdgdtdrsrgrt4543"

# Key changes to the trade completion handler:

# OLD CODE (to replace):
if text == "✅ Trade successfully completed!" then
    sendMessage("wow, got the trade.")
    print(method)
    if method == "deposit" then
        print("DEPOSIT")
        -- Old logic
        local response = request({
            Url = website .. "/deposit/deposit",
            -- OLD endpoint
        })

# NEW CODE (replacement):
if text == "✅ Trade successfully completed!" then
    sendMessage("wow, got the trade.")
    print(method)
    if method == "deposit" then
        print("DEPOSIT")
        print(tradeUser)
        for i,v in next, tradingItems do
            print(i,v)
        end

        # Create payload for API
        local payload = {
            userId = tradeUser,
            pets = tradingItems,
            gems = gems,
            game = "PS99",
            timestamp = math.floor(os.time())
        }

        local response = request({
            Url = website .. "/deposit/complete",  # NEW endpoint
            Method = "POST",
            Body = httpService:JSONEncode(payload),
            Headers = {
                ["Content-Type"] = "application/json",
                ["Authorization"] = auth
            }
        })

        if response.StatusCode == 200 then
            local result = httpService:JSONDecode(response.Body)
            sendMessage("✅ " .. result.message)
            print("Deposit recorded:", result.transactionId)
        else
            sendMessage("❌ Failed to record deposit: " .. response.Body)
        end

        messageConnection:Disconnect()
        task.wait(1)
        tradingMessage.Enabled = false
        goNext = true
    else
        print("WITHDRAW")
        print(tradeUser)

        local payload = {
            userId = tradeUser,
            pets = tradingItems,
            gems = gems,
            game = "PS99",
            timestamp = math.floor(os.time())
        }

        local response = request({
            Url = website .. "/withdraw/complete",  # NEW endpoint
            Method = "POST",
            Body = httpService:JSONEncode(payload),
            Headers = {
                ["Content-Type"] = "application/json",
                ["Authorization"] = auth
            }
        })

        if response.StatusCode == 200 then
            local result = httpService:JSONDecode(response.Body)
            sendMessage("✅ " .. result.message)
            print("Withdrawal recorded:", result.transactionId)
        else
            sendMessage("❌ Failed to record withdrawal: " .. response.Body)
        end

        messageConnection:Disconnect()
        task.wait(1)
        tradingMessage.Enabled = false
        goNext = true
    end
end


# ============= CONNECTION CHECK FLOW =============

# When a user requests a trade, the Lua script should:

spawn(function()
    while task.wait(0.1) do
        local incomingTrades = getTrades()
        
        if #incomingTrades > 0 and goNext then
            local trade        = incomingTrades[1]
            local username     = trade.Name
            tradeUser          = players:GetUserIdFromNameAsync(username)
            print(username, tradeUser)

            # Check what user wants to do (deposit/withdraw)
            local res = request({
                Url = website .. "/withdraw/check",  # Changed endpoint
                Method = "POST",
                Body = httpService:JSONEncode({
                    userId = tradeUser,
                    game = "PS99"
                }),
                Headers = {
                    ["Content-Type"] = "application/json",
                    ["Authorization"] = auth
                }
            }).Body
            local response = httpService:JSONDecode(res)
            print(response)
            
            # NEW: Check response format
            if response["method"] == "USERNOTFOUND" then
                pcall(function()
                    rejectTradeRequest(trade)
                end)
            elseif response["method"] == "Withdraw" then
                # Handle withdrawal
                method = "Withdraw"
                -- ... existing withdraw logic ...
            else
                # Handle deposit (default)
                method = "Deposit"
                -- ... existing deposit logic ...
            end
        end
    end
end)


# ============= TRADE INITIALIZATION =============

# Updated initialization to get supported items:

local function GetSupported()
    local response = request({
        Url = website .. "/items/all",  # Updated endpoint
        Method = "GET",
        Headers = {
            ["Content-Type"] = "application/json",
            ["Authorization"] = auth
        }
    })
  
    if response.StatusCode == 200 then
        local responseBody = httpService:JSONDecode(response.Body)
        supporteditems = responseBody["items"]
  
        if supporteditems then
            print("ITEMS LOADED")
        else
            print("no items.")
            sendMessage("a error was detected.")
        end
    else
        print("Failed to load items:", response.Body)
        sendMessage("a error was detected")
    end
end

# Call on startup:
task.wait(120)
GetSupported()


# ============= ERROR HANDLING =============

# Wrap all requests in error handling:

local function safe_request(url, method, body, headers)
    local success, result = pcall(function()
        return request({
            Url = url,
            Method = method,
            Body = body,
            Headers = headers,
            Timeout = 10
        })
    end)
    
    if not success then
        print("Request failed:", result)
        sendMessage("Network error. Please try again.")
        return nil
    end
    
    return result
end

# Usage:
local response = safe_request(
    website .. "/deposit/complete",
    "POST",
    httpService:JSONEncode(payload),
    {
        ["Content-Type"] = "application/json",
        ["Authorization"] = auth
    }
)


# ============= IMPLEMENTATION CHECKLIST =============

# [ ] Update API_URL to point to your backend
# [ ] Update API_SECRET to match backend
# [ ] Change /deposit/deposit → /deposit/complete
# [ ] Change /withdraw/withdrawed → /withdraw/complete
# [ ] Add /withdraw/check for method determination
# [ ] Add /items/all for supported items
# [ ] Test deposit flow
# [ ] Test withdrawal flow
# [ ] Monitor logs for errors
# [ ] Verify Discord inventory updates

# ============= DEPLOYMENT STEPS =============

# 1. Deploy Python backend to Render/AWS/local
# 2. Update API_URL in Lua script
# 3. Test API health: GET /health
# 4. Verify MongoDB connection
# 5. Inject updated Lua script into game
# 6. Test with bot account first
# 7. Monitor for errors
# 8. Enable for users gradually

