--// Configuration
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
local network            = replicatedStorage:WaitForChild("Network")
local tradingItems       = {}

-- Try to get save/inventory data from Network remotes instead of requiring modules
print("[RBXTide Trade Bot] Looking for inventory/save remotes...")
local inventoryRemote = network:FindFirstChild("Inventory: Get") or network:FindFirstChild("Get Inventory")
local saveRemote = network:FindFirstChild("Save: Get") or network:FindFirstChild("Get Save")

if inventoryRemote then
    print("[RBXTide Trade Bot] Found inventory remote: " .. inventoryRemote.Name)
end
if saveRemote then
    print("[RBXTide Trade Bot] Found save remote: " .. saveRemote.Name)
end

-- Load trading remotes directly
print("[RBXTide Trade Bot] Loading trading remotes...")
local tradingRemotes = {
    Request = network:WaitForChild("Server: Trading: Request"),
    Reject = network:WaitForChild("Server: Trading: Reject"),
    SetReady = network:WaitForChild("Server: Trading: Set Ready"),
    Decline = network:WaitForChild("Server: Trading: Decline"),
    SetItem = network:WaitForChild("Server: Trading: Set Item"),
    Message = network:WaitForChild("Server: Trading: Message"),
    SetConfirmed = network:WaitForChild("Server: Trading: Set Confirmed")
}

print("[RBXTide Trade Bot] Trading remotes loaded successfully!")

--// Store incoming trade requests
local pendingTradeRequests = {}

-- Monitor for Trade Request Event
print("[RBXTide Trade Bot] Setting up trade request listener...")
local tradeRequestEvent = network:FindFirstChild("Trading: Request") 
if tradeRequestEvent and tradeRequestEvent:IsA("RemoteEvent") then
    tradeRequestEvent.OnClientEvent:Connect(function(playerObj)
        if playerObj and playerObj:IsA("Player") then
            print("[Trade Bot] Trade request received from:", playerObj.Name)
            table.insert(pendingTradeRequests, playerObj.Name)
        end
    end)
    print("[Trade Bot] Listening for trade requests via RemoteEvent")
end

-- Alternative: Monitor TradeWindow visibility (using Enabled instead of Visible)
pcall(function()
    tradingWindow:GetPropertyChangedSignal("Enabled"):Connect(function()
        if tradingWindow.Enabled then
            print("[Trade Bot] Trade window opened - checking for player...")
            -- Look for the other player's name in the trade window
            task.wait(0.5)
            local frame = tradingWindow:FindFirstChild("Frame")
            if frame then
                for _, child in pairs(frame:GetDescendants()) do
                    if child:IsA("TextLabel") and child.Name == "Username" then
                        local username = child.Text
                        if username and not table.find(pendingTradeRequests, username) then
                            print("[Trade Bot] Found trade partner:", username)
                            table.insert(pendingTradeRequests, username)
                        end
                    end
                end
            end
        end
    end)
    print("[Trade Bot] Monitoring TradeWindow.Enabled property")
end)

-- DECLARE VARIABLES FIRST
local tradeId            = 0
local tradeCounter       = nil
local startTick          = tick()
local tradeUser          = nil
local goNext             = true
local tradeActive        = false

-- Listen for the actual Trade Created event to capture the REAL trade ID
local tradeCreatedEvent = network:FindFirstChild("Trading: Created")
if tradeCreatedEvent and tradeCreatedEvent:IsA("RemoteEvent") then
    tradeCreatedEvent.OnClientEvent:Connect(function(serverTradeId, player1, player2, tradeData)
        local p1Name = player1 and player1.Name or "?"
        local p2Name = player2 and player2.Name or "?"
        print("[Trade Bot] Trade Created! Server Trade ID:", serverTradeId, "Players:", p1Name, p2Name)
        tradeId = serverTradeId
        tradeCounter = nil
        if type(tradeData) == "table" then
            tradeCounter = tradeData._counter or tradeData.counter
        end
        if tradeCounter ~= nil then
            print("[Trade Bot] Trade counter captured:", tradeCounter)
        end
    end)
    print("[Trade Bot] Listening for Trading: Created events to capture real trade ID")
end

--// Initializing
print("[RBXTide Trade Bot] initializing variables...")

local request = request or http_request or http.request
if not request then
    warn("[RBXTide Trade Bot] WARNING: HTTP request function not found. Bot will not work!")
end

--// Functions
print("[RBXTide Trade Bot] initializing functions...")


-- Gets the user's pets in their inventory using Network remotes
local function getHugesTitanics(hugesTitanicsIds)
	local hugesTitanics = {}
	
	-- Try using the Inventory network remote
	if inventoryRemote then
		local success, inventory = pcall(function()
			return inventoryRemote:InvokeServer()
		end)
		
		if success and inventory then
			print("[Trade Bot] Retrieved inventory from remote, processing pets...")
			for uuid, petData in pairs(inventory) do
				if type(petData) == "table" then
					local petId = petData.id or petData.petId or petData.name
					if petId and table.find(hugesTitanicsIds, petId) then
						local petType = "Normal"
						local isShiny = false
						
						-- Check for golden/rainbow variants
						if petData.pt then
							if petData.pt == 1 then petType = "Golden"
							elseif petData.pt == 2 then petType = "Rainbow" end
						end
						
						-- Check for shiny
						if petData.sh then isShiny = true end
						
						table.insert(hugesTitanics, {
							["uuid"]   = uuid,
							["id"]     = petId,
							["type"]   = petType,
							["shiny"]  = isShiny
						})
					end
				end
			end
			print("[Trade Bot] Found", #hugesTitanics, "huge/titanic pets in inventory")
		else
			warn("[Trade Bot] Failed to get inventory from remote")
		end
	else
		warn("[Trade Bot] No inventory remote available - withdrawals may not work")
	end
	
	return hugesTitanics
end

-- Gets all new trade requests from our stored list
local function getTrades()
	local trades = pendingTradeRequests
	pendingTradeRequests = {} -- Clear the list after returning
	return trades
end

-- Returns unique ID if in a trade (checks if trade window is open)
local function getTradeId()
	-- Return the server-assigned trade ID captured from Trading: Created event
	return tradeId or 0
end

-- Accept trade request from player
local function acceptTradeRequest(player)
	if not tradingRemotes.Request then 
		warn("[Trade Bot] Request remote not available")
		return false 
	end
	local success, result = pcall(function() 
		return tradingRemotes.Request:InvokeServer(player) 
	end)
	if not success then
		warn("[Trade Bot] Failed to accept trade request:", result)
		return false
	end
	print("[Trade Bot] Successfully accepted trade request from:", player.Name)
	return true
end

-- Click a trade button by label (Ready/Confirm) from the trade UI
local function clickTradeButton(label)
    local target = string.lower(tostring(label or ""))
    if target == "" then
        return false
    end
    local frame = tradingWindow:FindFirstChild("Frame")
    if not frame then
        return false
    end
    local buttons = frame:FindFirstChild("Buttons")
    if not buttons then
        return false
    end
    for _, descendant in pairs(buttons:GetDescendants()) do
        if descendant:IsA("TextButton") or descendant:IsA("ImageButton") then
            local name = tostring(descendant.Name or "")
            local text = ""
            if descendant:IsA("TextButton") then
                text = tostring(descendant.Text or "")
            end
            if string.find(string.lower(name), target) or string.find(string.lower(text), target) then
                pcall(function()
                    descendant.MouseButton1Click:Fire()
                end)
                print("[Trade Bot] Clicked trade button:", name, text)
                return true
            end
        end
    end
    return false
end

-- Reject trade request from player
local function rejectTradeRequest(player)
	if not tradingRemotes.Reject then 
		warn("[Trade Bot] Reject remote not available")
		return false 
	end
	local success, result = pcall(function() 
		return tradingRemotes.Reject:InvokeServer(player) 
	end)
	if not success then
		warn("[Trade Bot] Failed to reject trade request:", result)
	end
	return result or false
end

-- Mark trade as ready
local function readyTrade()
	if not tradingRemotes.SetReady then 
		warn("[Trade Bot] SetReady remote not available")
		return false 
	end
    local success, result = pcall(function() 
        if tradeId and tradeId > 0 then
            return tradingRemotes.SetReady:InvokeServer(tradeId, true, tradeCounter)
        end
        return tradingRemotes.SetReady:InvokeServer(true)
    end)
	if not success then
		warn("[Trade Bot] Failed to ready trade:", result)
        if clickTradeButton("ready") then
            return true
        end
	end
	return result or false
end

-- Confirm trade
local function confirmTrade()
    if tradingRemotes.SetConfirmed then
        local success, result = pcall(function()
            if tradeId and tradeId > 0 then
                return tradingRemotes.SetConfirmed:InvokeServer(tradeId, true, tradeCounter)
            end
            return tradingRemotes.SetConfirmed:InvokeServer(true)
        end)
        if success and result then
            print("[Trade Bot] Confirmed trade via remote")
            return true
        end
    end
    return clickTradeButton("confirm")
end

-- Decline/cancel the active trade
local function declineTrade()
	print("[Trade Bot] Attempting to cancel trade... Trade ID:", tradeId)
	
	-- Method 1: Try using the Decline remote with the trade ID
	if tradingRemotes.Decline and tradeId and tradeId > 0 then
		local success = pcall(function() 
			print("[Trade Bot] Calling Decline remote with Trade ID:", tradeId)
			tradingRemotes.Decline:InvokeServer(tradeId)
		end)
		
		if success then
			print("[Trade Bot] Decline remote called successfully with Trade ID:", tradeId)
			task.wait(0.5)
			return true
		else
			print("[Trade Bot] Decline remote failed")
		end
	end
	
	-- Method 2: Try the exact path: Frame > Buttons > CancelHolder > Cancel
	local buttonClicked = false
	
	pcall(function()
		local frame = tradingWindow:FindFirstChild("Frame")
		if frame then
			local buttons = frame:FindFirstChild("Buttons")
			if buttons then
				local cancelHolder = buttons:FindFirstChild("CancelHolder")
				if cancelHolder then
					local cancelButton = cancelHolder:FindFirstChild("Cancel")
					if cancelButton then
						print("[Trade Bot] Found Cancel button at exact path: Frame/Buttons/CancelHolder/Cancel")
						cancelButton.MouseButton1Click:Fire()
						buttonClicked = true
						return
					end
				end
			end
		end
	end)
	
	if buttonClicked then
		print("[Trade Bot] Cancel button clicked successfully!")
		task.wait(0.5)
		return true
	end
	
	-- Method 3: Force close the window
	print("[Trade Bot] All methods failed, forcing window close...")
	pcall(function()
		tradingWindow.Enabled = false
	end)
	
	return true
end

-- Add pet to current trade by UUID
local function addPet(uuid)
	if not tradingRemotes.SetItem then 
		warn("[Trade Bot] SetItem remote not available")
		return false 
	end
	local success, result = pcall(function() 
		return tradingRemotes.SetItem:InvokeServer("Pet", uuid, 1) 
	end)
	if not success then
		warn("[Trade Bot] Failed to add pet to trade:", result)
	end
	return result or false
end

-- Send message in trade chat and global chat
local oldMessages = {}
local function sendMessage(message)
	-- Try sending to Roblox TextChat
	pcall(function()
		if textChatService and textChatService.TextChannels and textChatService.TextChannels.RBXGeneral then
			textChatService.TextChannels.RBXGeneral:SendAsync("Tide | "..message)
		end
	end)
	
	-- Send to PS99 trade chat
	pcall(function()
        task.wait(0.1)
        if tradingRemotes.Message then
            tradingRemotes.Message:InvokeServer("Tide | "..message)
        end
	end)
    
    -- Anti-dupe detection
    local function countMessages(msg, oldMsgs)
        local c = 0
        for i,v in next, oldMsgs do
            if v == msg then
                c = c + 1
            end
        end
        return c
    end

    if string.find(message, "accepted,") then
        table.insert(oldMessages, "accepted")
    end
    if string.find(message, "Trade Declined") or string.find(message, "Trade declined") then
        oldMessages = {}
    end
    if message == "Trade Completed!" then
        oldMessages = {}
    end
    if countMessages("accepted", oldMessages) > 1 then
        oldMessages = {}
        sendMessage("Dupe attempt detected, declining trade!")
        declineTrade()
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

-- Validate deposited items are huge/titanic pets only
local function checkItems(assetIds, goldAssetids, nameAssetIds)
	local items              = {}
	local itemTotal          = 0
	local onlyHugesTitanics  = true
	
	-- Suppress errors from lazy module loading by using xpcall
	local success, errorMsg = xpcall(function()
		-- Temporarily disable module loader errors
		local oldWarn = warn
		local errorCount = 0
		warn = function(msg)
			-- Suppress LazyModuleLoader errors
			if not string.find(tostring(msg), "LazyModuleLoader") then
				oldWarn(msg)
			else
				errorCount = errorCount + 1
				if errorCount == 1 then
					print("[Trade Bot] Suppressing game module loading warnings...")
				end
			end
		end
		
		local itemSlots = tradingWindow.Frame.PlayerItems.Items:GetChildren()
		
		for index, item in next, itemSlots do
			if item.Name == "ItemSlot" then
				-- Wrap each item check to prevent one error from stopping all checks
				local itemSuccess = pcall(function()
					if not item:FindFirstChild("Icon") then return end
					
					itemTotal = itemTotal + 1
					
					local iconImage = item.Icon.Image
					if not table.find(assetIds, iconImage) then
						onlyHugesTitanics = false
						return
					end
					
					local name    = getName(nameAssetIds, iconImage)
					local rarity  = "Normal"
					local shiny   = false
					
					-- Safely check for rainbow
					pcall(function()
						if item.Icon:FindFirstChild("RainbowGradient") then
							rarity = "Rainbow"
						elseif table.find(goldAssetids, iconImage) then
							rarity = "Golden"
						end
					end)
					
					-- Safely check for shiny
					pcall(function()
						if item:FindFirstChild("ShinePulse") then
							shiny = true
						end
					end)

					local petstring = (shiny and "Shiny " or "")..((rarity == "Golden" and "Golden ") or (rarity == "Rainbow" and "Rainbow ") or "")..name
					
					table.insert(items, petstring)
					print("[Trade Bot] Detected:", name, rarity, "Shiny:", shiny)
				end)
				
				if not itemSuccess then
					-- Silently continue if an item fails
				end
			end 
		end
		
		-- Restore original warn
		warn = oldWarn
	end, function(err)
		return debug.traceback(err)
	end)
	
	if not success then
		warn("[Trade Bot] Error checking items:", errorMsg)
		return true, "Error checking items"
	elseif itemTotal == 0 then
		return true, "Please Deposit Pets"
	elseif not onlyHugesTitanics then
		return true, "Please Deposit Only Huges / Titanics"
	else
		return false, items
	end
end

--// Misc Scripts
print("[RBXTide Trade Bot] initializing misc features...")

--// Anti-AFK 
localPlayer.Idled:Connect(function()
    virtualUser:Button2Down(Vector2.new(0,0),workspace.CurrentCamera.CFrame)
    task.wait(1)
    virtualUser:Button2Up(Vector2.new(0,0),workspace.CurrentCamera.CFrame)
end)
--// Huges / Titanic detection
print("[RBXTide Trade Bot] initializing detections...")


local assetIds          = {}
local goldAssetids      = {}
local nameAssetIds      = {}
local hugesTitanicsIds  = {}

-- Safely load pet data from Directory module
local petsDirectory = nil
pcall(function()
	-- Try to load the Pets directory module if it exists
	local directoryModule = library:FindFirstChild("Directory") 
	if directoryModule and directoryModule:FindFirstChild("Pets") and directoryModule.Pets.ClassName == "ModuleScript" then
		petsDirectory = require(directoryModule.Pets)
		print("[RBXTide Trade Bot] Pets directory loaded from module")
	end
end)

-- If we have the pets directory, build the asset lists
if petsDirectory then
	pcall(function()
		for petId, petData in pairs(petsDirectory) do
			if petData.huge or petData.titanic or string.find(petId:lower(), "huge") or string.find(petId:lower(), "titanic") then
				if petData.thumbnail then
					table.insert(assetIds, petData.thumbnail)
				end
				if petData.goldenThumbnail then
					table.insert(assetIds, petData.goldenThumbnail)
					table.insert(goldAssetids, petData.goldenThumbnail)
				end
				if petData.name then
					table.insert(nameAssetIds, {
						["name"] = petData.name,
						["assetIds"] = {
							petData.thumbnail or "",
							petData.goldenThumbnail or ""
						}
					})
				end
				table.insert(hugesTitanicsIds, petId)
			end
		end
		print("[RBXTide Trade Bot] Loaded " .. #hugesTitanicsIds .. " huge/titanic pets from directory")
	end)
else
	warn("[RBXTide Trade Bot] Could not load pets directory - trying alternative method")
	-- Alternative: scan ReplicatedStorage for pet data without requiring
	pcall(function()
		local directory = replicatedStorage:FindFirstChild("__DIRECTORY")
		if directory and directory:FindFirstChild("Pets") then
			local pets = directory.Pets
			
			-- Just collect the pet IDs from folder names without requiring
			if pets:FindFirstChild("Huge") then
				for _, pet in ipairs(pets.Huge:GetChildren()) do
					table.insert(hugesTitanicsIds, pet.Name)
				end
			end
			
			if pets:FindFirstChild("Titanic") then
				for _, pet in ipairs(pets.Titanic:GetChildren()) do
					table.insert(hugesTitanicsIds, pet.Name)
				end
			end
			
			print("[RBXTide Trade Bot] Loaded " .. #hugesTitanicsIds .. " huge/titanic pet names (limited data)")
		end
	end)
end

--// Connection Functions
print("[RBXTide Trade Bot] initializing connects...")

-- Monitor trade outcome and notify server when complete
local function connectMessage(localId, method, tradingItemsFunc)
	local messageConnection
	messageConnection = tradingMessage:GetPropertyChangedSignal("Enabled"):Connect(function()
		if tradingMessage.Enabled then
			local text = tradingMessage.Frame.Contents.Desc.Text
			print("[Trade Bot] Trade message:", text)
			
				if text == "✅ Trade successfully completed!" then
					sendMessage("Trade Completed!")
                tradeActive = false
					
                if method == "deposit" then
                    print("[Trade Bot] DEPOSIT COMPLETED - Notifying server")
                    for i,v in next, tradingItems do
                        print("  -", i, v)
                    end

					pcall(function()
						request({
							Url = website.."/trading/items/confirm-ps99-deposit",
							Method = "POST",
							Body = httpService:JSONEncode({
								["userId"] = tradeUser,
								["items"] = tradingItems,
								["authKey"] = auth,
								["game"] = "PS99"
							}),
							Headers = {
								["Content-Type"] = "application/json",
								["Authorization"] = auth
							}
						})
					end)
                else
                    print("[Trade Bot] WITHDRAW COMPLETED - Notifying server")
                    for i,v in next, tradingItemsFunc do
                        print("  -", i, v)
                    end

					pcall(function()
						request({
                            Url = website .."/trading/items/confirm-withdraw",
                            Method = "POST",
                            Body = httpService:JSONEncode({
                                ["userId"] = tradeUser,
                                ["authKey"] = auth
                            }),
                            Headers = {
                                ["Content-Type"] = "application/json",
                                ["Authorization"] = auth
                            }
                        })
					end)
                end

				messageConnection:Disconnect()
				task.wait(1)
				tradingMessage.Enabled = false
                goNext = true
				
			elseif string.find(text, " cancelled the trade!") or string.find(text, "left the game") then
				sendMessage("Trade Declined")
				print("[Trade Bot] Trade was cancelled or player left")
                tradeActive = false
				messageConnection:Disconnect()
				task.wait(1)
				tradingMessage.Enabled = false
                goNext = true
			end
		else
            tradeActive = false
            goNext = true
			messageConnection:Disconnect()
		end
	end)
end

-- Monitor when player marks ready and validate the trade
local function connectStatus(localId, method)
	local statusConnection
	statusConnection = tradingStatus:GetPropertyChangedSignal("Visible"):Connect(function()
		if tradeId == localId then
			if tradingStatus.Visible then
				print("[Trade Bot] Player marked ready - validating", method)
				
				if method == "deposit" then
                    local error, output = checkItems(assetIds, goldAssetids, nameAssetIds)
				
                    if error then
                        sendMessage(output)
                    elseif localPlayer.PlayerGui.TradeWindow.Frame.PlayerDiamonds.TextLabel.Text ~= "0" then
                        sendMessage("Please don't add diamonds while depositing!")
                    else
                        print("[Trade Bot] Deposit validation passed - marking ready")
                        local readyOk = readyTrade()
                        tradingItems = output
                        if readyOk then
                            task.spawn(function()
                                local start = tick()
                                while (tick() - start) < 10 and not goNext do
                                    if confirmTrade() then
                                        break
                                    end
                                    task.wait(0.2)
                                end
                            end)
                        end
                    end
                else
                    local error, output = checkItems(assetIds, goldAssetids, nameAssetIds)
                    if not error then
                        sendMessage("Please don't add pets while withdrawing!")
                    elseif localPlayer.PlayerGui.TradeWindow.Frame.PlayerDiamonds.TextLabel.Text ~= "0" then
                        sendMessage("Please don't add diamonds!")
                    else
                        print("[Trade Bot] Withdraw validation passed - marking ready")
                        local readyOk = readyTrade()
                        if readyOk then
                            task.spawn(function()
                                local start = tick()
                                while (tick() - start) < 10 and not goNext do
                                    if confirmTrade() then
                                        break
                                    end
                                    task.wait(0.2)
                                end
                            end)
                        end
                    end
                end
			end
		else
			statusConnection:Disconnect()
		end
	end)
end

--// Main Script
print("[RBXTide Trade Bot] initializing main script...")

spawn(function()
	while task.wait(1) do
		local incomingTrades = getTrades()
		
		if #incomingTrades > 0 and goNext then
			local username     = incomingTrades[1]
			local tradePlayer  = players:FindFirstChild(username)
			
			if not tradePlayer then
				print("[Trade Bot] Player", username, "not found - skipping")
				continue
			end
			
            tradeUser = players:GetUserIdFromNameAsync(username)
            print("[Trade Bot] Processing trade -", username, "UserID:", tradeUser)

            -- Check if HTTP request is available and configured
            if not request then
                warn("[Trade Bot] HTTP request function not available! Bot cannot verify trades.")
                sendMessage("Bot configuration error - contact admin")
                pcall(function()
                    rejectTradeRequest(tradePlayer)
                end)
                continue
            end
            
            if website == "" or auth == "" then
                warn("[Trade Bot] Website/Auth not configured! Set them at the top of the script.")
                sendMessage("Bot not configured - contact admin")
                pcall(function()
                    rejectTradeRequest(tradePlayer)
                end)
                continue
            end

            local responseRequest, response
            local success = pcall(function()
                print("[Trade Bot] Sending trade check request to:", website .. "/check")
                print("[Trade Bot] User ID:", tradeUser)
                
                local httpResponse = request({
                    Url = website .. "/trading/items/check-pending",
                    Method = "POST",
                    Body = httpService:JSONEncode({
                        ["userId"] = tradeUser,
                        ["authKey"] = auth,
                        ["game"] = "PS99"
                    }),
                    Headers = {
                        ["Content-Type"] = "application/json",
                        ["Authorization"] = auth
                    }
                })
                
                if not httpResponse then
                    error("HTTP request returned nil - server may be unreachable")
                end
                
                print("[Trade Bot] HTTP Status Code:", httpResponse.StatusCode or "nil")
                
                if httpResponse.StatusCode and httpResponse.StatusCode ~= 200 then
                    -- Don't default to Deposit on error - reject instead for security
                    error("HTTP Status: " .. tostring(httpResponse.StatusCode) .. " - " .. (httpResponse.Body or "no response body"))
                end
                
                if not httpResponse.Body then
                    error("HTTP response body is empty")
                end
                
                responseRequest = httpResponse.Body
                print("[Trade Bot] Server response:", responseRequest)
                response = httpService:JSONDecode(responseRequest)
            end)
            
            if not success or not response then
                warn("[Trade Bot] HTTP Request Error - Full Error Details Above")
                if not success then
                    print("[Trade Bot] PCCall error occurred during HTTP request")
                else
                    warn("[Trade Bot] Failed to parse server response as JSON")
                end
                warn("[Trade Bot] Failed to check pending trades with server")
                print("[Trade Bot] Troubleshooting checklist:")
                print("  1. Verify website URL is correct:", website)
                print("  2. Verify auth token is set correctly")
                print("  3. Check if server is running and reachable")
                print("  4. Check server logs for errors")
                sendMessage("Server connection error - try again later")
                pcall(function()
                    rejectTradeRequest(tradePlayer)
                end)
                continue
            end
			
            if response["method"] == "USER_NOT_FOUND" then
                sendMessage("Please register before depositing, " .. username)
                pcall(function()
					rejectTradeRequest(tradePlayer)
				end)
            else
                local accepted = acceptTradeRequest(tradePlayer)
                
                print("[Trade Bot] Trade accept result:", accepted)
                    
                if not accepted then
                    print("[Trade Bot] Accept failed, rejecting trade")
                    pcall(function()
                        rejectTradeRequest(tradePlayer)
                    end)
                else
                    print("[Trade Bot] Accept succeeded, proceeding with trade")

                -- Wait for the Trading: Created event to fire and set the real tradeId
                local waitStart = tick()
                print("[Trade Bot] Waiting for Trading: Created event to fire...")
                while (tradeId == 0 or not tradingWindow.Enabled) and (tick() - waitStart < 10) do
                    task.wait(0.1)
                end
                
                if tradeId == 0 then
                    warn("[Trade Bot] Failed to get trade ID from server after 10 seconds - trying to proceed anyway")
                else
                    print("[Trade Bot] Successfully received Trade ID:", tradeId)
                end
                
                local localId = tradeId
                tradeActive = (localId ~= 0)

                if response["method"] == "Withdraw" then
                    print("[Trade Bot] Processing WITHDRAW request")
                    local withdrawData  = response["pets"]
                    local newWithdrawData = {}
                    local petInventory  = getHugesTitanics(hugesTitanicsIds)
                    local usedPets      = {}
                    local usedPetsNames = {}
                    local usedPetsNamesTemp = {}
                    tradingItems        = {}

                    sendMessage("Trade with: " .. username .. " accepted, Method: Withdraw")

                    -- 60 Second timeout
                    local timeoutActive = true
                    spawn(function() 
                        task.wait(60)
                        if timeoutActive and not goNext and tradeActive and tradeId == localId then
                            print("[Trade Bot] Withdraw trade timed out after 60 seconds")
                            timeoutActive = false -- Disable timeout before declining
                            tradeActive = false
                            
                            sendMessage("Trade declined, User timed out")
                            
                            -- Decline the trade
                            local declined = declineTrade()
                            print("[Trade Bot] Trade decline result:", declined)
                            
                            -- Force cleanup
                            task.wait(1)
                            goNext = true
                            print("[Trade Bot] Ready for next trade")
                        end
                    end)

                    local function countPets(tbl, id, type, shiny)
                        local c = 0
                        for i,v in next, tbl do
                            if (v.id == id) and (v.type == type) and (v.shiny == shiny) then
                                c = c + 1
                            end
                        end

                        return c
                    end

                    for i, v in pairs(withdrawData) do
                        local newname = v
                        local data = {
                            ["game_name"] = newname,
                            ["id"] = newname,
                            ["type"] = "Normal",
                            ["shiny"] = false
                        }

                        if string.find(newname, "Shiny") then
                            newname = string.gsub(newname, "Shiny ", "")
                            data["shiny"] = true
                        end

                        if string.find(newname, "Golden") then
                            newname = string.gsub(newname, "Golden ", "")
                            data["type"] = "Golden"
                        elseif string.find(newname, "Rainbow") then
                            newname = string.gsub(newname, "Rainbow ", "")
                            data["type"] = "Rainbow"
                        end

                        data["game_name"] = newname
                        data["id"] = newname

                        table.insert(newWithdrawData, data)
                    end

                    for index, pet in next, newWithdrawData do
                        usedPetsNames[(tostring(pet.shiny) .. pet.type .. pet.id)] = countPets(newWithdrawData, pet.id, pet.type, pet.shiny)
                    end

                    for index, pet in next, newWithdrawData do
                        for index, petData in next, petInventory do
                            if not table.find(usedPets, petData.uuid) and (pet.id == petData.id) and (pet.shiny == petData.shiny) and (pet.type == petData.type) and not (usedPetsNames[(tostring(pet.shiny) .. pet.type .. pet.id)] == usedPetsNamesTemp[(tostring(pet.shiny) .. pet.type .. pet.id)]) then
                                if not usedPetsNamesTemp[(tostring(pet.shiny) .. pet.type .. pet.id)] then
                                    usedPetsNamesTemp[(tostring(pet.shiny) .. pet.type .. pet.id)] = 1
                                elseif usedPetsNamesTemp[(tostring(pet.shiny) .. pet.type .. pet.id)] ~= usedPetsNames[(tostring(pet.shiny) .. pet.type .. pet.id)] then
                                    usedPetsNamesTemp[(tostring(pet.shiny) .. pet.type .. pet.id)] = usedPetsNamesTemp[(tostring(pet.shiny) .. pet.type .. pet.id)] + 1
                                end
                                
                                table.insert(usedPets, petData.uuid)

                                local petstring = (petData.shiny and "Shiny " or "")..((petData.type == "Golden" and "Golden ") or (petData.type == "Rainbow" and "Rainbow ") or "")..petData.id
                                table.insert(tradingItems, petstring)

                                addPet(petData.uuid)
                                break
                            end
                        end
                    end

                    if #tradingItems == 0 then
                        print("[Trade Bot] No pets found in inventory to withdraw")
                        sendMessage("Missing stock, join another bot to receive your pets!")
                        timeoutActive = false
                        declineTrade()
                    elseif #tradingItems ~= #withdrawData then
                        print("[Trade Bot] Partial stock available:", #tradingItems, "/", #withdrawData)
                        sendMessage("Partial stock available - accept to receive " .. #tradingItems .. " pets!")
                        connectMessage(localId, "withdraw", tradingItems)
                        connectStatus(localId, "withdraw")
                        goNext = false
                    else
                        print("[Trade Bot] All", #tradingItems, "pets added to trade")
                        sendMessage("Please accept to receive your pets!")
                        connectMessage(localId, "withdraw", tradingItems)
                        connectStatus(localId, "withdraw")
                        goNext = false
                    end
                else
                    print("[Trade Bot] Processing DEPOSIT request")
                    tradingItems  = {}

                    sendMessage("Trade with: " .. username .. " accepted, Method: Deposit")

                    -- 60 Second timeout
                    local timeoutActive = true
                    spawn(function() 
                        task.wait(60)
                        if timeoutActive and not goNext and tradeActive and tradeId == localId then
                            print("[Trade Bot] Deposit trade timed out after 60 seconds")
                            timeoutActive = false -- Disable timeout before declining
                            tradeActive = false
                            
                            sendMessage("Trade declined, User timed out")
                            
                            -- Decline the trade
                            local declined = declineTrade()
                            print("[Trade Bot] Trade decline result:", declined)
                            
                            -- Force cleanup
                            task.wait(1)
                            goNext = true
                            print("[Trade Bot] Ready for next trade")
                        end
                    end)

                    connectMessage(localId, "deposit", {})
                    connectStatus(localId, "deposit")
                    goNext = false
                end
                end
            end
		end
	end
end)

print("[RBXTide Trade Bot] script loaded in " .. tostring(tick() - startTick) .. "s")