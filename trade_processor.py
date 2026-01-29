"""
Trade validation and processing logic
Validates pets, gems, and trade integrity
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class TradeType(Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"


@dataclass
class TradeItem:
    """Represents a pet in a trade"""
    name: str
    rarity: str  # "Normal", "Golden", "Rainbow"
    shiny: bool
    quantity: int = 1
    
    @property
    def display_name(self) -> str:
        """Get formatted pet name with rarity and shiny status"""
        prefix = "Shiny " if self.shiny else ""
        rarity_prefix = {
            "Golden": "Golden ",
            "Rainbow": "Rainbow ",
            "Normal": ""
        }.get(self.rarity, "")
        return f"{prefix}{rarity_prefix}{self.name}".strip()


@dataclass
class TradeData:
    """Complete trade request data"""
    type: TradeType
    user_id: int
    pets: List[TradeItem]
    gems: int = 0
    code: Optional[str] = None  # Security code
    timestamp: Optional[float] = None


class TradeValidator:
    """Validates trades against rules and inventory"""
    
    # Deposit constraints
    MIN_GEM_DEPOSIT = 50_000_000  # 50M
    MAX_GEM_DEPOSIT = 10_000_000_000  # 10B
    GEM_DEPOSIT_MULTIPLE = 50_000_000  # Must be multiples of 50M
    
    # Withdrawal constraints
    MAX_BOT_GEM_BALANCE = 100_000_000_000  # 100B
    
    def __init__(self, supported_pets: List[str], pet_values: Dict[str, int]):
        """
        Initialize validator with supported pets and their values
        
        Args:
            supported_pets: List of pet names the bot can trade
            pet_values: Dict mapping pet names to their values
        """
        self.supported_pets = {pet.lower() for pet in supported_pets}
        self.pet_values = pet_values
    
    def validate_deposit(self, trade: TradeData) -> Tuple[bool, str]:
        """
        Validate a deposit trade
        
        Returns:
            (is_valid, error_message)
        """
        # Check pets
        if trade.pets:
            for pet in trade.pets:
                if pet.display_name.lower() not in self.supported_pets:
                    return False, f"Pet '{pet.display_name}' is not supported. Only Huge and Titanic pets accepted."
        
        # Check gems
        if trade.gems > 0:
            if trade.gems < self.MIN_GEM_DEPOSIT:
                return False, f"Minimum gem deposit is {self.MIN_GEM_DEPOSIT:,}"
            if trade.gems > self.MAX_GEM_DEPOSIT:
                return False, f"Maximum gem deposit is {self.MAX_GEM_DEPOSIT:,}"
            if trade.gems % self.GEM_DEPOSIT_MULTIPLE != 0:
                return False, f"Gems must be in multiples of {self.GEM_DEPOSIT_MULTIPLE:,}"
        
        # Must deposit something
        if not trade.pets and trade.gems == 0:
            return False, "Please deposit pets or gems"
        
        return True, ""
    
    def validate_withdraw(self, trade: TradeData, inventory: Dict[str, int]) -> Tuple[bool, str]:
        """
        Validate a withdrawal trade
        
        Returns:
            (is_valid, error_message)
        """
        # Check if user has requested items
        for pet in trade.pets:
            inventory_key = pet.display_name.lower()
            available = inventory.get(inventory_key, 0)
            if available < pet.quantity:
                return False, f"You don't have enough '{pet.display_name}'. Available: {available}, Requested: {pet.quantity}"
        
        # Withdrawals don't need gems
        if trade.gems > 0:
            return False, "Cannot withdraw gems (only pets are tradeable)"
        
        # Must withdraw something
        if not trade.pets:
            return False, "No pets to withdraw"
        
        return True, ""
    
    def validate_trade_contents(self, items: List[TradeItem], gems: int) -> Tuple[bool, str]:
        """Validate the contents of a trade before execution"""
        # Check all pets are supported
        unsupported = []
        for item in items:
            if item.display_name.lower() not in self.supported_pets:
                unsupported.append(item.display_name)
        
        if unsupported:
            return False, f"Unsupported items: {', '.join(unsupported)}"
        
        return True, ""
    
    def calculate_deposit_value(self, items: List[TradeItem]) -> int:
        """Calculate total value of deposited pets"""
        total = 0
        for item in items:
            value = self.pet_values.get(item.display_name, 0)
            total += value * item.quantity
        return total
    
    def get_pet_value(self, pet_name: str) -> int:
        """Get value of a specific pet"""
        return self.pet_values.get(pet_name, 0)


class TradeProcessor:
    """Processes validated trades"""
    
    def __init__(self, db, security_manager):
        """
        Initialize processor
        
        Args:
            db: Database instance
            security_manager: Security manager for payload signing
        """
        self.db = db
        self.security = security_manager
    
    async def process_deposit(self, discord_id: int, roblox_user_id: int, trade_data: TradeData) -> Dict:
        """
        Process a deposit transaction
        
        Returns:
            Transaction record
        """
        # Calculate total deposit value
        pet_values = await self.db.get_all_pet_values()
        validator = TradeValidator([], pet_values)
        deposit_value = validator.calculate_deposit_value(trade_data.pets)
        
        # Record transaction
        transaction = await self.db.record_transaction({
            "type": "deposit",
            "discord_id": discord_id,
            "roblox_user_id": roblox_user_id,
            "pets": [
                {
                    "name": pet.display_name,
                    "rarity": pet.rarity,
                    "shiny": pet.shiny,
                    "quantity": pet.quantity
                }
                for pet in trade_data.pets
            ],
            "gems": trade_data.gems,
            "total_value": deposit_value,
            "status": "pending",
            "code": trade_data.code
        })
        
        # Add pets to inventory
        for pet in trade_data.pets:
            for _ in range(pet.quantity):
                await self.db.add_pet_to_inventory(
                    discord_id,
                    pet.display_name,
                    pet_data={
                        "rarity": pet.rarity,
                        "shiny": pet.shiny,
                        "deposited_at": trade_data.timestamp
                    }
                )
        
        # Add gems to balance
        if trade_data.gems > 0:
            await self.db.update_gem_balance(discord_id, trade_data.gems)
        
        # Mark transaction as completed
        await self.db.transactions.update_one(
            {"_id": transaction},
            {"$set": {"status": "completed"}}
        )
        
        return {"transaction_id": transaction, "status": "success"}
    
    async def process_withdraw(self, discord_id: int, roblox_user_id: int, trade_data: TradeData) -> Dict:
        """
        Process a withdrawal transaction
        
        Returns:
            Transaction record with requested items
        """
        # Record transaction
        transaction = await self.db.record_transaction({
            "type": "withdraw",
            "discord_id": discord_id,
            "roblox_user_id": roblox_user_id,
            "pets": [
                {
                    "name": pet.display_name,
                    "rarity": pet.rarity,
                    "shiny": pet.shiny,
                    "quantity": pet.quantity
                }
                for pet in trade_data.pets
            ],
            "status": "pending",
            "code": trade_data.code
        })
        
        # Remove pets from inventory
        for pet in trade_data.pets:
            await self.db.remove_pet_from_inventory(
                discord_id,
                pet.display_name,
                pet.quantity
            )
        
        # Mark transaction as completed
        await self.db.transactions.update_one(
            {"_id": transaction},
            {"$set": {"status": "completed"}}
        )
        
        return {"transaction_id": transaction, "status": "success"}
