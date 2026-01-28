

local website = "https://susurrus-quiddity.onrender.com"
local auth = "xK9mL2pQ7vW5nR8jT4cD6hF1sA3bE5gJ7kN0oP2qR4sT6uV8wX0yZ2cA4dB6eC8fD0"

--// Variables
local players            = game:GetService("Players")
local replicatedStorage  = game:GetService("ReplicatedStorage")
local httpService        = game:GetService("HttpService")
local virtualUser        = game:GetService("VirtualUser")
local textChatService    = game:GetService("TextChatService")

local localPlayer        = players.LocalPlayer
local playerGUI          = localPlayer:WaitForChild("PlayerGui")
local tradingWindow      = playerGUI:WaitForChild("TradeWindow")
local tradingMessage     = playerGUI:WaitForChild("Message")
local tradingStatus      = tradingWindow:WaitForChild("Frame"):WaitForChild("PlayerItems"):WaitForChild("Status")
local tradingMessages    = tradingWindow:WaitForChild("Frame"):WaitForChild("ChatOverlay"):WaitForChild("Messages")

local library            = replicatedStorage:WaitForChild("Library")
local saveModule         = nil
local tradingCommands    = nil

-- Try to require game modules (may fail in executor environments)
local success1, result1 = pcall(function()
    return require(library:WaitForChild("Client"):WaitForChild("Save"))
end)
if success1 then
    saveModule = result1
    print("[SUCCESS] Save module loaded")
else
    print("[FAILED] Could not load Save module:", result1)
end

local success2, result2 = pcall(function()
    return require(library:WaitForChild("Client"):WaitForChild("TradingCmds"))
end)
if success2 then
    tradingCommands = result2
    print("[SUCCESS] TradingCmds module loaded")
else
    print("[FAILED] Could not load TradingCmds module:", result2)
end

local tradingItems       = {}
local supporteditems     = {}


local tradeId            = 0
local startTick          = tick()

local tradeUser          = nil
local goNext             = true

local gems = 0

local method = nil

--// Initializing
print("[SPIN Trade Bot] initializing variables...")

local request = request or http_request or http.request
local websocket = websocket or WebSocket
local getHwid = getuseridentifier or get_user_identifier or gethwid or get_hwid

--// Functions
print("[SPIN Trade Bot] initializing functions...")

-- Gets the user's pets in their inventory
local function getHugesTitanics(hugesTitanicsIds)
	local hugesTitanics = {}
	if not saveModule then return hugesTitanics end
	
	for uuid, pet in next, saveModule.Get().Inventory.Pet do
		if table.find(hugesTitanicsIds, pet.id) then
			table.insert(hugesTitanics, {
                ["uuid"]   = uuid,
                ["id"]     = pet.id,
                ["type"]   = (pet.pt == 1 and "Golden") or (pet.pt == 2 and "Rainbow") or "Normal",
                ["shiny"]  = pet.sh or false
            })
		end
	end
	
	return hugesTitanics
end

-- Gets the user's diamonds
local function getDiamonds()
	if not saveModule then return 0 end
	for currencyUid, currency in next, saveModule.Get().Inventory.Currency do
		if currency.id == "Diamonds" then
			return currency._am, currencyUid
		end
	end
	
	return 0
end

-- Gets all new trade requests
local function getTrades()
	local trades          = {}
	if not tradingCommands then 
		print("[WARNING] tradingCommands is nil - cannot get trades")
		return trades 
	end
	print("[DEBUG] getTrades() called - checking for incoming trades...")
	local functionTrades  = tradingCommands.GetAllRequests()
	print("[DEBUG] GetAllRequests returned:", type(functionTrades), "with", (#functionTrades or "?"), "items")
	
	for player, trade in next, functionTrades do
		if trade[localPlayer] then
			table.insert(trades, player)
		end
	end
	
	if #trades > 0 then
		print("[DEBUG] Found", #trades, "incoming trade(s)")
	end
	return trades
end



local function strictgem() -- Gets Player Gems clean.
    local gems_value = game.Players.LocalPlayer.PlayerGui.MainLeft.Left.Currency.Diamonds.Diamonds.Amount.Text
    return gems_value
  end
  local function client_currencies_gems() -- Fetches the gems from the player's GUI and not recommend using this for looking/comparing stats.
    local gems_value = game.Players.LocalPlayer.PlayerGui.MainLeft.Left.Currency.Diamonds.Diamonds.Amount.Text -- retry fixed
    local cleanText = dmca:gsub(",", "")
    local gemNumber = tonumber(cleanText)
    return gemNumber
  end
  
  local function client_trade_gems() -- You/Bot gems.
    local gemText = localPlayer.PlayerGui.TradeWindow.Frame.ClientDiamonds.Diamonds.Input.PlaceholderText
    return gemText
  end
  local function client_trade_gems_2() --client_trade_gems_2 other player
    local gemText = localPlayer.PlayerGui.TradeWindow.Frame.PlayerDiamonds.TextLabel.Text
    local cleanText = gemText:gsub(",", "")
    local gemNumber = tonumber(cleanText)
    return gemNumber
  end

-- Returns 0 if your not in a trade
local function getTradeId()
	if not tradingCommands then return 044443 end
	return (tradingCommands.GetState() and tradingCommands.GetState()._id) or 044443
end
-- Accept trade request
local function acceptTradeRequest(player)
	if not tradingCommands then return false end
	return tradingCommands.Request(player)
end
-- Reject trade request
local function rejectTradeRequest(player)
	if not tradingCommands then return false end
	return tradingCommands.Reject(player)
end
-- Readys the actual trade
local function readyTrade()
	if not tradingCommands then return false end
	return tradingCommands.SetReady(true)
end
-- Declines the actual trade
local function declineTrade()
	if not tradingCommands then return false end
	return tradingCommands.Decline()
end

local function confirmTrade()
	if not tradingCommands then return false end
    return tradingCommands.SetConfirmed(true) 
end


-- Adds pet to trade
local function addPet(uuid)
	if not tradingCommands then return false end
	return tradingCommands.SetItem("Pet", uuid, 1)
end

local function addGems(amount)
	if not tradingCommands then return false end
    return tradingCommands.SetCurrency("Diamonds", amount)
  end 


-- Chat message (In Chat / PS99 Chat)
local oldMessages = {}
local function sendMessage(message)
    pcall(function()
        textChatService.TextChannels.RBXGeneral:SendAsync(message)
    end)
    pcall(function()
        task.wait(0.1)
    end)

    local function countMessages(message, oldMessages)
        local c = 0
        for i,v in next, oldMessages do
            if v == message then
                c = c + 1
            end
        end

        return c
    end

    if string.find(message, "accepted,") then
        print("Ins - mes")
        table.insert(oldMessages, "accepted")
    end
    if string.find(message, " Trade Declined") or string.find(message, " Trade declined") then
        if tradingWindow then
            tradingWindow.Visible = false 
            task.wait(1)
            tradingWindow.Visible = false 
            goNext = true
        end
        print("Declined - mes")
        oldMessages = {}
    end
    if message == "Trade Completed!" then
        print("Completed - mes")
        oldMessages = {}
    end

    return true
end
-- Gets name of pet through asset id
local function getName(assetIds, assetId)
	for index, petData in next, assetIds do
		if table.find(petData.assetIds, assetId) then
			return petData.name
		end
	end
	
	return "???"
end


-- Check for huges / titanics
local function checkItems(assetIds, goldAssetIds, nameAssetIds)
    local items = {}
    local itemTotal = 0
    local onlyHugesTitanics = true
    local unsupported = {}
  
    print(supporteditems)
  
    for index, item in next, tradingWindow.Frame.PlayerItems.Items:GetChildren() do
        if item.Name == "ItemSlot" then
            itemTotal = itemTotal + 1
  
            if not table.find(assetIds, item.Icon.Image) then
                onlyHugesTitanics = false
                break
            end
  
            local name = getName(nameAssetIds, item.Icon.Image)
            
            local rarity = (item.Icon:FindFirstChild("RainbowGradient") and "Rainbow") or
                           (table.find(goldAssetIds, item.Icon.Image) and "Golden") or
                           "Normal"
            
            local shiny = (item:FindFirstChild("ShinePulse") and true) or false
  

            local petString = (shiny and "Shiny " or "")..
                              ((rarity == "Golden" and "Golden ") or (rarity == "Rainbow" and "Rainbow ") or "")..
                              name
            print(petString)
  
            if not table.find(supporteditems, petString) then
              table.insert(unsupported, petString)
              print("UNSUPPORTED!")
          end
            
            table.insert(items, petString)
  
            print(name, rarity, shiny)
        end 
    end
  
    if itemTotal == 0 then
        if client_trade_gems_2() > 0 then
            return false, items  
        else
            return true, "Please Deposit Pets or gems" 
        end
    end
  
    if not onlyHugesTitanics then
        return true, "Please Deposit Only Huges / Titanics or gems" 
    end
  
    if #unsupported >= 1 then
      return true, "remove from trade : " .. table.concat(unsupported, ",")
    end
  
    return false, items
  end
  

--// Misc Scripts
print("[bloxy Trade Bot] initializing misc features...")

localPlayer.Idled:Connect(function()
    virtualUser:Button2Down(Vector2.new(0,0),workspace.CurrentCamera.CFrame)
    task.wait(1)
    virtualUser:Button2Up(Vector2.new(0,0),workspace.CurrentCamera.CFrame)
end)

--// Huges / Titanic detection
print("[spinnyblox Trade Bot] initializing detections...")

local assetIds          = {}
local goldAssetids      = {}
local nameAssetIds      = {}
local hugesTitanicsIds  = {}


local function GetSupported()
    local response = request({
      Url = website .. "/items/all?game=PS99",
      Method = "GET",
      Headers = {
          ["Content-Type"] = "application/json",
          ["Authorization"] = auth
      }
    })
  
    print("GetSupported Status Code:", response.StatusCode)
    print("GetSupported Response Body:", response.Body)
    
    if response.StatusCode == 200 then
      local responseBody = httpService:JSONDecode(response.Body)
      print("Decoded response:", httpService:JSONEncode(responseBody))
      supporteditems = responseBody["items"]
      
      print("supporteditems type:", type(supporteditems))
      if supporteditems then
        print("supporteditems count:", #supporteditems)
      end
  
      if supporteditems and #supporteditems > 0 then
        print("ITEMS LOADDED - Count:", #supporteditems)
      else
        print("No items returned from API")
        sendMessage("No supported items configured. Please add items to the system.")
      end
    else
      print("API returned error status:", response.StatusCode)
      sendMessage("API connection error. Status: " .. tostring(response.StatusCode))
    end
  end

-- Huges
for index, pet in next, replicatedStorage.__DIRECTORY.Pets.Huge:GetChildren() do
	local success, petData = pcall(function() return require(pet) end)
	if success and petData then
		table.insert(assetIds, petData.thumbnail)
		table.insert(assetIds, petData.goldenThumbnail)
		table.insert(goldAssetids, petData.goldenThumbnail)
		table.insert(nameAssetIds, {
			["name"]      = petData.name,
			["assetIds"]  = {
				petData.thumbnail,
				petData.goldenThumbnail
			}
		})
		table.insert(hugesTitanicsIds, petData._id)
	end
end
-- Titanics
for index, pet in next, replicatedStorage.__DIRECTORY.Pets.Titanic:GetChildren() do
	local success, petData = pcall(function() return require(pet) end)
	if success and petData then
		table.insert(assetIds, petData.thumbnail)
		table.insert(assetIds, petData.goldenThumbnail)
		table.insert(goldAssetids, petData.goldenThumbnail)
		table.insert(nameAssetIds, {
			["name"]      = petData.name,
			["assetIds"]  = {
				petData.thumbnail,
				petData.goldenThumbnail
			}
		})
		table.insert(hugesTitanicsIds, petData._id)
	end
end

--// Trade ID setting
spawn(function()
	while task.wait(0.5) do
		tradeId = getTradeId()
	end
end)

--// Connection Functions
print("[bloxy Trade Bot] initializing connects...")

-- Detect accept / declining of the trade
local function connectMessage(localId, method, tradingItemsFunc)
	local messageConnection
	messageConnection = tradingMessage:GetPropertyChangedSignal("Enabled"):Connect(function()
        print(tradingMessage.Enabled)
		if tradingMessage.Enabled then
			local text = tradingMessage.Frame.Contents.Desc.Text
			
			if text == "✅ Trade successfully completed!" then -- Accepted the trade
				sendMessage("wow, got the trade.")
                print(method)
                if method == "deposit" then
                    
                    print("DEPOSIT")
                    print(tradeUser)
                    print(securityKey)
                    for i,v in next, tradingItems do
                        print(i,v)
                    end

                    local response = request({
                        Url = website .. "/deposit/deposit",
                        Method = "POST",
                        Body = httpService:JSONEncode({
                          ["userId"] = tradeUser,
                          ["pets"] = tradingItems,
                          ["gems"] = gems,
                          ["game"] = "PS99"
                        }),
                        Headers = {
                          ["Content-Type"] = "application/json",
                          ["Authorization"] = auth
                        }
                      })

                    messageConnection:Disconnect()
                    print("MESSAGE DISCONNECTION", localId, tradeId, tradeUser, 5)
                    task.wait(1)
                    tradingMessage.Enabled = false
                    goNext = true
                else
                    print("withdraw :)")

                    print(tradeUser)

                    print("CONFIRM PARTIAL WITHDRAW")
                    print(tradeUser)
                    print(securityKey)
                    for i,v in next, tradingItemsFunc do
                        print(i,v)
                    end

                    print("trading items: ", tradingItems)

                    request({
                        Url = website .. "/withdraw/withdrawed",
                        Method = "POST",
                        Body = httpService:JSONEncode({
                          ["userId"] = tradeUser,
                          ["pets"] = tradingItems,
                          ["gems"] = gems
                        }),
                        Headers = {
                          ["Content-Type"] = "application/json",
                          ["Authorization"] = auth
                        }
                      })
                    end

                print("MESSAGE DISCONNECTION", localId, tradeId, tradeUser, 4)
				messageConnection:Disconnect()
				
				task.wait(1)
				tradingMessage.Enabled = false
                goNext = true
			elseif (string.find(text, " cancelled the trade!")) then -- Declined the trade
				sendMessage("Trade Declined")
                print("MESSAGE DISCONNECTION", localId, tradeId, tradeUser, 3)
				messageConnection:Disconnect()
				
				task.wait(1)
				tradingMessage.Enabled = false
                goNext = true
            elseif string.find(text, "left the game") then
                sendMessage("Trade Declined")
                print("MESSAGE DISCONNECTION", localId, tradeId, tradeUser, 2)
                messageConnection:Disconnect()
				
				task.wait(1)
				tradingMessage.Enabled = false
                goNext = true
			end
		else
            print("MESSAGE DISCONNECTION", localId, tradeId, tradeUser, 1)
            goNext = true
            task.wait(1)
            tradingMessage.Enabled = false
            goNext = true
			messageConnection:Disconnect()
		end
	end)
end
-- Detect when user accepts, make various checks, and accepts the trade
local function connectStatus(localId, method)
    local statusConnection
    statusConnection = tradingStatus:GetPropertyChangedSignal("Visible"):Connect(function()
        if tradeId == localId then
            if tradingStatus.Visible then
                if method == "deposit" then
                    local error, output = checkItems(assetIds, goldAssetids, nameAssetIds)
                    tradingItems = output
                    if error then
                        sendMessage(output)
                      elseif client_trade_gems_2() >= 1 and client_trade_gems_2() < 50000000 then
                        sendMessage("The min to deposit is 50 million!")
                    elseif client_trade_gems_2() > 10000000000 then
                        sendMessage("Please don't deposit more than 10 billion gems!")
                    elseif client_trade_gems_2() > 50000000 and client_trade_gems_2() % 50000000 ~= 0 then
                        sendMessage("please deposit always 50m blocks: (50m,100m, 150m, ect.)")
                    elseif localPlayer.PlayerGui.TradeWindow.Frame.PlayerDiamonds.TextLabel.Text == "100B" then
                      sendMessage("i've reached the max gems. deposit rap.")
                    else 
                        gems = client_trade_gems_2()
                        readyTrade()
                        confirmTrade()
                    end
                elseif method == "withdraw" then
                    local error, output = checkItems(assetIds, goldAssetids, nameAssetIds)
                    print(error)
                    if not error then
                        sendMessage("Please don't add pets while withdrawing!")
                    elseif client_trade_gems_2() > 0 then
                        sendMessage("Please don't add diamonds while withdrawing!")
                        print("wiithdraw checker")
                    else
                        readyTrade()
                        confirmTrade()
                    end
                end
            end
        else
            statusConnection:Disconnect()
        end
    end)
  end
--// Main Script
print("[spinn Trade Bot] initializing main script...")

-- Since tradingCommands module isn't available, detect trades via UI changes
-- Listen for when trading window becomes visible (indicates incoming trade)
spawn(function()
	local lastTradeId = nil
	
	while task.wait(0.1) do
		if tradingWindow.Visible then
			-- Trading window is open - check if this is a new trade
			local currentTradeId = getTradeId()
			
			if currentTradeId ~= lastTradeId and currentTradeId ~= 044443 then
				print("[DEBUG] New trade detected! Trade ID:", currentTradeId)
				lastTradeId = currentTradeId
				
				-- Try to get the other player's name from the UI
				-- This might vary depending on game structure
				local username = "Unknown"
				pcall(function()
					-- Try to find username in trade window UI
					local playerItems = tradingWindow:FindFirstChild("Frame"):FindFirstChild("PlayerItems")
					if playerItems then
						-- The username might be displayed somewhere in the trade window
						username = "Incoming_Trader"
					end
				end)
				
				print("[WARNING] Unable to get trader name from UI - using placeholder")
				print("[DEBUG] Assuming trade is from verified account since window opened")
				
				-- Since we can't get the username reliably, we need another approach
				-- For now, assume the trade is legitimate and accept it
				if goNext then
					goNext = false
					
					-- Accept the trade
					local accepted = acceptTradeRequest(tradingWindow)
					print("[DEBUG] Trade acceptance result:", accepted)
					
					if accepted then
						print("[DEBUG] Successfully accepted trade")
						sendMessage("Hello, we trading!")
						sendMessage("Code-12345")  -- Placeholder code
						
						-- Set up the connection handlers
						connectMessage(currentTradeId, "deposit", {})
						connectStatus(currentTradeId, "deposit")
					else
						print("[DEBUG] Failed to accept trade")
						goNext = true
					end
				end
			end
		else
			lastTradeId = nil
		end
	end
end)

spawn(function()
    task.wait(120)
    GetSupported()
  end)



print("[bloxyspinny Trade Bot] script loaded in " .. tostring(tick() - startTick) .. "s")
GetSupported()
