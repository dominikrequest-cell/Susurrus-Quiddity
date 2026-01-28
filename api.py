"""
FastAPI backend for trade processing
Handles API requests from Lua bot, Discord interactions, and trade validation
"""

from fastapi import FastAPI, HTTPException, Header, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import os

from database import Database
from roblox_verification import RobloxVerification
from trade_processor import TradeProcessor, TradeValidator, TradeData, TradeType, TradeItem
from security_manager import SecurityManager


# Initialize components
app = FastAPI(title="Pet Trading Bot API")

db = Database()
roblox = RobloxVerification(db)
security = SecurityManager(api_secret=os.getenv("API_SECRET", "default-secret-key"))
trade_processor = TradeProcessor(db, security)


# ============== Request/Response Models ==============

class DepositRequest(BaseModel):
    """Deposit request from Lua bot"""
    userId: int
    pets: List[Dict]  # [{"name": "...", "rarity": "...", "shiny": bool}]
    gems: int
    game: str = "PS99"
    signature: Optional[str] = None
    timestamp: Optional[float] = None


class WithdrawRequest(BaseModel):
    """Withdraw request to get data about what user wants"""
    userId: int
    game: str = "PS99"


class WithdrawReplyRequest(BaseModel):
    """Withdraw reply from Lua bot confirming trade"""
    userId: int
    pets: List[Dict]  # Pets being withdrawn
    gems: int
    game: str = "PS99"
    signature: Optional[str] = None
    timestamp: Optional[float] = None


class VerificationRequest(BaseModel):
    """Discord user verification request"""
    robloxUsername: str


class VerificationResponse(BaseModel):
    """Verification response with code"""
    code: str
    message: str


# ============== Verification Endpoints ==============

@app.post("/verify/start")
async def start_verification(request: VerificationRequest):
    """
    Start verification process
    User provides their Roblox username, gets a code to put in bio
    """
    # Validate username format
    is_valid, error = security.is_valid_username(request.robloxUsername)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Check if Roblox user exists
    user_id = await roblox.get_user_id(request.robloxUsername)
    if not user_id:
        raise HTTPException(status_code=404, detail="Roblox user not found")
    
    # Generate verification code
    code = security.generate_verification_code()
    
    # Store code in session (in real implementation, use cache/session storage)
    # For now, code is returned for user to put in bio
    
    return {
        "success": True,
        "code": code,
        "message": f"Please add this code to your Roblox bio: {code}",
        "robloxUsername": request.robloxUsername,
        "robloxUserId": user_id
    }


@app.post("/verify/confirm")
async def confirm_verification(
    robloxUsername: str,
    discordId: int,
    discordUsername: str = None
):
    """
    Confirm verification by checking if code is in user's Roblox bio
    Called by Discord bot after user provides their username
    """
    # Get Roblox user ID
    user_id = await roblox.get_user_id(robloxUsername)
    if not user_id:
        raise HTTPException(status_code=404, detail="Roblox user not found")
    
    # Get verification code for this user from cache
    # (In production, store code in Redis with TTL)
    # For now, we'll generate a new one and check
    
    # Check if code is in bio (placeholder - would need to store code somewhere)
    # This is a simplified version; full implementation would:
    # 1. Store generated code in Redis
    # 2. Check if user put it in their bio
    # 3. Link accounts after verification
    
    # Link Discord to Roblox
    await db.link_discord_to_roblox(
        discord_id=discordId,
        roblox_user_id=user_id,
        discord_username=discordUsername
    )
    
    return {
        "success": True,
        "message": f"Successfully verified {robloxUsername}",
        "robloxUserId": user_id
    }


# ============== Trade Endpoints ==============

@app.post("/deposit/check")
async def check_deposit(request: DepositRequest):
    """
    Check if user can deposit
    Lua calls this before trade to validate
    """
    # Verify signature
    payload_copy = request.dict()
    signature = payload_copy.pop("signature", None)
    if signature:
        is_valid, error = security.verify_payload({**payload_copy, "signature": signature})
        if not is_valid:
            raise HTTPException(status_code=401, detail=f"Invalid signature: {error}")
    
    # Get linked Discord user
    discord_user = await db.get_discord_user_by_roblox(request.userId)
    if not discord_user:
        raise HTTPException(status_code=404, detail="User not verified")
    
    # Parse pet data
    pets = [
        TradeItem(
            name=pet["name"],
            rarity=pet.get("rarity", "Normal"),
            shiny=pet.get("shiny", False)
        )
        for pet in request.pets
    ]
    
    # Get supported pets and their values
    supported_pets = ["Huge", "Titanic"]  # Would fetch from DB in real implementation
    pet_values = await db.get_all_pet_values()
    
    # Validate
    validator = TradeValidator(supported_pets, pet_values)
    is_valid, error = validator.validate_deposit(
        TradeData(
            type=TradeType.DEPOSIT,
            user_id=request.userId,
            pets=pets,
            gems=request.gems
        )
    )
    
    if not is_valid:
        return {"valid": False, "error": error}
    
    return {
        "valid": True,
        "discordUserId": discord_user["discord_id"],
        "depositValue": validator.calculate_deposit_value(pets)
    }


@app.post("/deposit/complete")
async def complete_deposit(request: DepositRequest):
    """
    Complete a deposit transaction
    Called by Lua after successful trade
    """
    # Verify signature
    is_valid, error = security.verify_payload({
        "userId": request.userId,
        "pets": request.pets,
        "gems": request.gems,
        "signature": request.signature or "",
        "timestamp": request.timestamp or 0
    })
    if not is_valid:
        raise HTTPException(status_code=401, detail=f"Invalid signature: {error}")
    
    # Get Discord user
    discord_user = await db.get_discord_user_by_roblox(request.userId)
    if not discord_user:
        raise HTTPException(status_code=404, detail="User not verified")
    
    # Process deposit
    pets = [
        TradeItem(
            name=pet["name"],
            rarity=pet.get("rarity", "Normal"),
            shiny=pet.get("shiny", False)
        )
        for pet in request.pets
    ]
    
    trade_data = TradeData(
        type=TradeType.DEPOSIT,
        user_id=request.userId,
        pets=pets,
        gems=request.gems,
        timestamp=request.timestamp
    )
    
    result = await trade_processor.process_deposit(
        discord_id=discord_user["discord_id"],
        roblox_user_id=request.userId,
        trade_data=trade_data
    )
    
    return {
        "success": True,
        "transactionId": result["transaction_id"],
        "message": f"Deposit of {len(pets)} pets and {request.gems:,} gems completed!"
    }


@app.post("/withdraw/method")
async def get_withdraw_method(request: WithdrawRequest):
    """
    Determine if user wants to deposit or withdraw
    This is called first to check if user is verified and has inventory
    """
    # Get Discord user by Roblox ID
    discord_user = await db.get_discord_user_by_roblox(request.userId)
    if not discord_user:
        return {"method": "USERNOTFOUND"}
    
    # Get user's inventory
    inventory = await db.get_inventory(discord_user["discord_id"])
    gems = await db.get_user_gem_balance(discord_user["discord_id"])
    
    # If user has items in inventory, they want to withdraw
    if inventory or gems > 0:
        # Convert inventory to pet list format
        pets = []
        for inv in inventory:
            for _ in range(inv["quantity"]):
                pets.append(inv["pet_name"])
        
        return {
            "method": "Withdraw",
            "pets": pets,
            "gems": gems,
            "code": security.generate_verification_code()[:6]  # Short security code
        }
    else:
        # User has no inventory, they want to deposit
        return {
            "method": "Deposit",
            "pets": [],
            "gems": 0,
            "code": security.generate_verification_code()[:6]
        }


@app.post("/withdraw/check")
async def check_withdraw(request: WithdrawRequest):
    """
    Check what user wants to withdraw
    Returns their inventory
    """
    # Get Discord user
    discord_user = await db.get_discord_user_by_roblox(request.userId)
    if not discord_user:
        return {"method": "USERNOTFOUND"}
    
    # Check if user has pending withdrawal request (from Discord bot)
    # This would come from Discord bot commands
    # For now, return inventory
    
    inventory = await db.get_inventory(discord_user["discord_id"])
    
    # Convert inventory to pet list format
    pets = [inv["pet_name"] for inv in inventory for _ in range(inv["quantity"])]
    gems = await db.get_user_gem_balance(discord_user["discord_id"])
    
    return {
        "method": "Withdraw",
        "pets": pets,
        "gems": gems,
        "code": "verification-code-here"  # Would be actual security code
    }


@app.post("/withdraw/complete")
async def complete_withdraw(request: WithdrawReplyRequest):
    """
    Complete a withdrawal transaction
    Called by Lua after successful trade
    """
    # Get Discord user
    discord_user = await db.get_discord_user_by_roblox(request.userId)
    if not discord_user:
        raise HTTPException(status_code=404, detail="User not verified")
    
    # Process withdraw
    pets = [
        TradeItem(
            name=pet["name"],
            rarity=pet.get("rarity", "Normal"),
            shiny=pet.get("shiny", False)
        )
        for pet in request.pets
    ]
    
    trade_data = TradeData(
        type=TradeType.WITHDRAW,
        user_id=request.userId,
        pets=pets,
        gems=request.gems,
        timestamp=request.timestamp
    )
    
    result = await trade_processor.process_withdraw(
        discord_id=discord_user["discord_id"],
        roblox_user_id=request.userId,
        trade_data=trade_data
    )
    
    return {
        "success": True,
        "transactionId": result["transaction_id"],
        "message": f"Withdrawal of {len(pets)} pets completed!"
    }


# ============== Admin/Management Endpoints ==============

@app.get("/items/all")
async def get_all_items(game: str = "PS99"):
    """
    Get all supported items and their values
    Called by Lua to validate trades
    """
    pet_values = await db.get_all_pet_values(game)
    
    return {
        "items": list(pet_values.keys()),
        "values": pet_values,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/user/{discord_id}/inventory")
async def get_user_inventory(discord_id: int):
    """Get user's current inventory"""
    inventory = await db.get_inventory(discord_id)
    gems = await db.get_user_gem_balance(discord_id)
    
    return {
        "discordId": discord_id,
        "pets": inventory,
        "gems": gems,
        "totalPets": sum(inv["quantity"] for inv in inventory)
    }


@app.get("/user/{discord_id}/transactions")
async def get_user_transactions(discord_id: int, limit: int = 50):
    """Get user's transaction history"""
    transactions = await db.get_user_transactions(discord_id, limit)
    
    return {
        "discordId": discord_id,
        "transactions": transactions,
        "count": len(transactions)
    }


# ============== Health Checks ==============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
