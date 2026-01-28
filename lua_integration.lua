"""
Updated Lua handler module for Roblox bot
This provides helper functions to securely communicate with the Python API
"""

# Lua integration helper functions to include in ps99lua.lua

local function create_signed_payload(user_id, pets, gems, trade_type)
    """Create a signed payload for the API"""
    local payload = {
        userId = user_id,
        pets = pets or {},
        gems = gems or 0,
        game = "PS99",
        timestamp = math.floor(os.time())
    }
    
    -- Note: Signature is created by Python backend using HMAC-SHA256
    -- Lua should send this as-is, and backend will verify
    -- For now, just send the payload
    return httpService:JSONEncode(payload)
end

local function send_trade_notification(webhook_url, trade_data)
    """Send trade notification to Discord webhook (optional)"""
    local payload = {
        content = string.format(
            "Trade completed: %s - %d pets, %d gems",
            trade_data.type,
            #trade_data.pets,
            trade_data.gems
        ),
        embeds = {
            {
                title = trade_data.type == "deposit" and "💰 Deposit" or "🎁 Withdrawal",
                fields = {
                    {name = "User ID", value = tostring(trade_data.userId)},
                    {name = "Pets", value = tostring(#trade_data.pets)},
                    {name = "Gems", value = string.format("%,d", trade_data.gems)}
                },
                color = trade_data.type == "deposit" and 3066993 or 7506394
            }
        }
    }
    
    local response = request({
        Url = webhook_url,
        Method = "POST",
        Body = httpService:JSONEncode(payload),
        Headers = {
            ["Content-Type"] = "application/json"
        }
    })
    
    return response.StatusCode == 204
end

-- Enhanced trade completion handler
local function handle_trade_completion(trade_type, user_id, pets, gems)
    """Handle successful trade with API notification"""
    
    local endpoint = string.format("%s/%s/complete", website, trade_type == "deposit" and "deposit" or "withdraw")
    
    local payload = {
        userId = user_id,
        pets = pets,
        gems = gems,
        game = "PS99"
    }
    
    local response = request({
        Url = endpoint,
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
        return true
    else
        sendMessage("❌ Failed to record trade. Contact support.")
        return false
    end
end

-- Export functions
return {
    create_signed_payload = create_signed_payload,
    send_trade_notification = send_trade_notification,
    handle_trade_completion = handle_trade_completion
}
