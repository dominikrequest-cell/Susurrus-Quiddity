

local website = "https://api.bloxyspin.org"
local auth = "SEXILOVE2024SGWdgdtdrsrgrt4543"

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
local saveModule         = require(library:WaitForChild("Client"):WaitForChild("Save"))
local tradingCommands    = require(library:WaitForChild("Client"):WaitForChild("TradingCmds"))
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
	local functionTrades  = tradingCommands.GetAllRequests()
	
	for player, trade in next, functionTrades do
		if trade[localPlayer] then
			table.insert(trades, player)
		end
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
	return (tradingCommands.GetState() and tradingCommands.GetState()._id) or 044443
end
-- Accept trade request
local function acceptTradeRequest(player)
	return tradingCommands.Request(player)
end
-- Reject trade request
local function rejectTradeRequest(player)
	return tradingCommands.Reject(player)
end
-- Readys the actual trade
local function readyTrade()
	return tradingCommands.SetReady(true)
end
-- Declines the actual trade
local function declineTrade()
	return tradingCommands.Decline()
end

local function confirmTrade()
    return tradingCommands.SetConfirmed(true) 
end


-- Adds pet to trade
local function addPet(uuid)
	return tradingCommands.SetItem("Pet", uuid, 1)
end

local function addGems(amount)
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
      Url = website .. "/items/all",
      Method = "POST",
      Body = httpService:JSONEncode({
          ["game"] = "PS99"
      }),
      Headers = {
          ["Content-Type"] = "application/json",
          ["Authorization"] = auth
      }
    })
  
    if response.StatusCode == 200 then
      local responseBody = httpService:JSONDecode(response.Body)
      supporteditems = responseBody["items"]
  
      if supporteditems then
        print("ITEMS LOADDED")
      else
        print("no items.")
        sendMessage("a error was detected.")
      end
    else
      sendMessage("a error was detected")
    end
  end

-- Huges
for index, pet in next, replicatedStorage.__DIRECTORY.Pets.Huge:GetChildren() do
	local petData = require(pet)
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
-- Titanics
for index, pet in next, replicatedStorage.__DIRECTORY.Pets.Titanic:GetChildren() do
	local petData = require(pet)
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

spawn(function()
	while task.wait(0.1) do
		local incomingTrades = getTrades()
		
		if #incomingTrades > 0 and goNext then
			local trade        = incomingTrades[1]
			local username     = trade.Name
            tradeUser          = players:GetUserIdFromNameAsync(username)
            print(username, tradeUser)

            local res = request({
                Url = website .. "/withdraw/method",
                Method = "POST",
                Body = httpService:JSONEncode({
                    ["userId"] = tradeUser,
                    ["game"] = "PS99"
                }),
                Headers = {
                    ["Content-Type"] = "application/json",
                    ["Authorization"] = auth
                }
            }).Body
            local response = httpService:JSONDecode(res)
            print(response)
			
            if response["method"] == "USERNOTFOUND" then
                pcall(function()
					rejectTradeRequest(trade)
				end)
            else
                local accepted = acceptTradeRequest(trade)
                    
                if not accepted then
                    pcall(function()
                        rejectTradeRequest(trade)
                    end)
                end

                local localId  = getTradeId()
                tradeId        = localId
                method = response["method"]

                if response["method"] == "Withdraw" then -- Withdraw
                    local withdrawData  = response["pets"]
                    local newWithdrawData = {}
                    local petInventory  = getHugesTitanics(hugesTitanicsIds)
                    local usedPets      = {}
                    local usedPetsNames = {}
                    local usedPetsNamesTemp = {}
                    tradingItems        = {}
                    gems = 0
                
                    sendMessage("Hello, " .. username .. " we trading!")
                    if response["code"] then
                        sendMessage(response["code"])
                    else
                        sendMessage("Please get a code for secure trades!")
                    end
                    -- 60 Second max
                    spawn(function() 
                        task.wait(140)
                        if tradeId == localId then
                            sendMessage("Trade declined")
                            declineTrade()
                            goNext = true
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
                
                    task.wait(0.3)
                    print("GEMS", response["gems"])
                    if response["gems"] >= 1 then
                        gems = response["gems"]
                        addGems(response["gems"])
                    end
                
                    if #tradingItems == 0 and response["gems"] == 0 then
                        sendMessage("no stock of your withdrawl, join another bot.")
                        if tradeId == localId then
                            sendMessage("Trade declined")
                            declineTrade()
                        end
                    elseif #tradingItems ~= #withdrawData then
                        local missingPets = {}
                    
                        for _, withdrawPet in ipairs(withdrawData) do
                            local found = false
                            for _, tradingPet in ipairs(tradingItems) do
                                if withdrawPet == tradingPet then
                                    found = true
                                    break
                                end
                            end
                            if not found then
                                table.insert(missingPets, withdrawPet)
                            end
                        end
                        
                        if #missingPets > 0 then
                            print("Missing pets: " .. table.concat(missingPets, ", "))
                            sendMessage("Missing stock, join another bot to receive your other pets!")
                        end
                
                        connectMessage(localId, "withdraw", tradingItems)
                        connectStatus(localId, "withdraw")
                        goNext = false
                        confirmTrade()
                    elseif #tradingItems == #withdrawData then
                        sendMessage("Please accept to receive your pets!")
                        connectMessage(localId, "withdraw", tradingItems)
                        connectStatus(localId, "withdraw")
                        goNext = false
                        confirmTrade()
                    end
                else -- Deposit
                    tradingItems  = {}

                    sendMessage("Hello, " .. username .. " we trading!")
                    if response["code"] then
                        sendMessage(response["code"])
                    else
                        sendMessage("Please get a code for secure trades!")
                    end

                    -- 60 Second max
                    spawn(function() 
                        task.wait(140)
                        if tradeId == localId then
                            sendMessage("Trade declined")
                            declineTrade()
                        end
                    end)

                    connectMessage(localId, "deposit", {})
                    connectStatus(localId, "deposit")
                    goNext = false
                end
            end
		end
	end
end)

spawn(function()
    task.wait(120)
    GetSupported()
  end)



print("[bloxyspinny Trade Bot] script loaded in " .. tostring(tick() - startTick) .. "s")
GetSupported()
