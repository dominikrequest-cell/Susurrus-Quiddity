"""
Database abstraction layer for user data, inventory, and transaction tracking
Uses MongoDB for scalability
"""

from pymongo import MongoClient, UpdateOne
from datetime import datetime
from typing import Optional, Dict, List
import os


class Database:
    """MongoDB database handler"""
    
    def __init__(self, connection_url: str = None):
        self.connection_url = connection_url or os.getenv("MONGODB_URL")
        self.client = MongoClient(self.connection_url)
        self.db = self.client["pet_trading_bot"]
        
        # Collections
        self.users = self.db["users"]
        self.inventory = self.db["inventory"]
        self.transactions = self.db["transactions"]
        self.discord_users = self.db["discord_users"]
        self.pet_values = self.db["pet_values"]
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        self.users.create_index("user_id", unique=True)
        self.users.create_index("username")
        self.discord_users.create_index("discord_id", unique=True)
        self.discord_users.create_index("roblox_user_id")
        self.inventory.create_index([("discord_id", 1), ("pet_name", 1)])
        self.transactions.create_index("discord_id")
        self.transactions.create_index("roblox_user_id")
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get Roblox user data by ID"""
        return self.users.find_one({"user_id": user_id})
    
    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get Roblox user data by username"""
        return self.users.find_one({"username": username})
    
    async def insert_or_update_user(self, user_id: int, username: str):
        """Insert or update Roblox user in database"""
        self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "username": username,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )
    
    async def update_user_description(self, user_id: int, description: str):
        """Update user's Roblox bio"""
        self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "description": description,
                    "description_updated_at": datetime.utcnow()
                }
            }
        )
    
    async def update_user_thumbnail(self, user_id: int, thumbnail_url: str):
        """Update user's avatar thumbnail"""
        self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "thumbnail": thumbnail_url,
                    "thumbnail_updated_at": datetime.utcnow()
                }
            }
        )
    
    async def get_user_description(self, user_id: int) -> Optional[str]:
        """Get cached user description"""
        user = self.users.find_one({"user_id": user_id})
        return user.get("description") if user else None
    
    async def get_user_thumbnail(self, user_id: int) -> Optional[str]:
        """Get cached user thumbnail"""
        user = self.users.find_one({"user_id": user_id})
        return user.get("thumbnail") if user else None
    
    # Discord User Linking
    async def link_discord_to_roblox(self, discord_id: int, roblox_user_id: int, roblox_username: str, discord_username: str = None):
        """Link Discord user to Roblox account"""
        self.discord_users.update_one(
            {"discord_id": discord_id},
            {
                "$set": {
                    "discord_id": discord_id,
                    "roblox_user_id": roblox_user_id,
                    "roblox_username": roblox_username,
                    "discord_username": discord_username,
                    "verified": True,
                    "verified_at": datetime.utcnow()
                },
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )
    
    async def get_discord_user(self, discord_id: int) -> Optional[Dict]:
        """Get Discord user and their linked Roblox account"""
        return self.discord_users.find_one({"discord_id": discord_id})
    
    async def get_discord_user_by_roblox(self, roblox_user_id: int) -> Optional[Dict]:
        """Get Discord user by their linked Roblox account"""
        return self.discord_users.find_one({"roblox_user_id": roblox_user_id})
    
    async def unlink_discord_from_roblox(self, discord_id: int):
        """Unlink a Discord user from their Roblox account"""
        self.discord_users.delete_one({"discord_id": discord_id})
    
    # Inventory Management
    async def get_inventory(self, discord_id: int) -> List[Dict]:
        """Get Discord user's pet inventory"""
        return list(self.inventory.find({"discord_id": discord_id}))
    
    async def add_pet_to_inventory(self, discord_id: int, pet_name: str, quantity: int = 1, pet_data: Dict = None):
        """Add pet to user's inventory"""
        self.inventory.update_one(
            {"discord_id": discord_id, "pet_name": pet_name},
            {
                "$inc": {"quantity": quantity},
                "$set": {
                    "pet_data": pet_data or {},
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "discord_id": discord_id,
                    "pet_name": pet_name,
                    "quantity": quantity,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
    
    async def remove_pet_from_inventory(self, discord_id: int, pet_name: str, quantity: int = 1):
        """Remove pet from user's inventory"""
        self.inventory.update_one(
            {"discord_id": discord_id, "pet_name": pet_name},
            {
                "$inc": {"quantity": -quantity},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        # Remove if quantity reaches 0
        self.inventory.delete_one({"discord_id": discord_id, "pet_name": pet_name, "quantity": {"$lte": 0}})
    
    async def get_user_gem_balance(self, discord_id: int) -> int:
        """Get user's gem balance"""
        user = self.discord_users.find_one({"discord_id": discord_id})
        return user.get("gem_balance", 0) if user else 0
    
    async def update_gem_balance(self, discord_id: int, amount: int):
        """Update user's gem balance"""
        self.discord_users.update_one(
            {"discord_id": discord_id},
            {
                "$inc": {"gem_balance": amount},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
    
    # Transactions
    async def record_transaction(self, transaction_data: Dict) -> str:
        """Record a deposit/withdrawal transaction"""
        transaction_data["created_at"] = datetime.utcnow()
        result = self.transactions.insert_one(transaction_data)
        return str(result.inserted_id)
    
    async def get_transaction(self, transaction_id: str) -> Optional[Dict]:
        """Get transaction by ID"""
        from bson import ObjectId
        return self.transactions.find_one({"_id": ObjectId(transaction_id)})
    
    async def get_user_transactions(self, discord_id: int, limit: int = 50) -> List[Dict]:
        """Get user's transaction history"""
        return list(self.transactions.find({"discord_id": discord_id}).sort("created_at", -1).limit(limit))
    
    # Pet Values
    async def update_pet_value(self, pet_name: str, value: int, scraper_timestamp: datetime = None):
        """Update pet value from scraper"""
        self.pet_values.update_one(
            {"pet_name": pet_name},
            {
                "$set": {
                    "pet_name": pet_name,
                    "value": value,
                    "updated_at": datetime.utcnow(),
                    "scraper_timestamp": scraper_timestamp or datetime.utcnow()
                },
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )
    
    async def get_pet_value(self, pet_name: str) -> Optional[int]:
        """Get pet's current value"""
        pet = self.pet_values.find_one({"pet_name": pet_name})
        return pet.get("value") if pet else None
    
    async def get_all_pet_values(self) -> Dict[str, int]:
        """Get all pet values"""
        pets = self.pet_values.find({})
        return {pet["pet_name"]: pet["value"] for pet in pets}
    
    def close(self):
        """Close database connection"""
        self.client.close()
