"""
Database abstraction layer for user data, inventory, and transaction tracking
Uses MongoDB for scalability
"""

from pymongo import MongoClient, UpdateOne, errors
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure
from datetime import datetime
from typing import Optional, Dict, List
import os
import urllib.parse


def safe_db_operation(func):
    """Decorator to safely handle database operations with graceful failures"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (OperationFailure, ServerSelectionTimeoutError, Exception) as e:
            print(f"[DB Error] {func.__name__}: {e}")
            return None
    return wrapper


class Database:
    """MongoDB database handler"""
    
    def __init__(self, connection_url: str = None):
        self.connection_url = connection_url or os.getenv("MONGODB_URL")
        self.db_available = False
        
        try:
            # URL encode the connection string if needed
            if "mongodb+srv://" in self.connection_url:
                try:
                    # Try connecting with current URL
                    self.client = MongoClient(self.connection_url, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
                    # Test connection
                    self.client.admin.command('ping')
                    self.db_available = True
                    print("[MongoDB] ✅ Connected successfully")
                except (ServerSelectionTimeoutError, OperationFailure) as e:
                    print(f"[MongoDB] ⚠️  Connection failed: {str(e)[:100]}")
                    print("[MongoDB] ⚠️  Bot will continue without database")
                    # Try with minimal connection
                    self.client = MongoClient(self.connection_url, maxPoolSize=1, serverSelectionTimeoutMS=2000)
                    self.db_available = False
            else:
                self.client = MongoClient(self.connection_url)
                self.db_available = True
        except Exception as e:
            print(f"[MongoDB] ❌ Failed to initialize: {e}")
            self.db_available = False
            # Create dummy client
            self.client = None
            
        if self.client:
            self.db = self.client["pet_trading_bot"]
            
            # Collections
            self.users = self.db["users"]
            self.inventory = self.db["inventory"]
            self.transactions = self.db["transactions"]
            self.discord_users = self.db["discord_users"]
            self.pet_values = self.db["pet_values"]
            
            # Create indexes (gracefully)
            self._create_indexes()
        else:
            self.db = None
            self.users = None
            self.inventory = None
            self.transactions = None
            self.discord_users = None
            self.pet_values = None
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            self.users.create_index("user_id", unique=True)
            self.users.create_index("username")
            self.discord_users.create_index("discord_id", unique=True)
            self.discord_users.create_index("roblox_user_id")
            self.inventory.create_index([("discord_id", 1), ("pet_name", 1)])
            self.transactions.create_index("discord_id")
            self.transactions.create_index("roblox_user_id")
        except Exception as e:
            print(f"Warning: Could not create indexes - {e}")
            print("Continuing without indexes...")
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get Roblox user data by ID"""
        try:
            return self.users.find_one({"user_id": user_id})
        except Exception as e:
            print(f"[DB Error] get_user_by_id: {e}")
            return None
    
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
        try:
            if self.discord_users is not None:
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
        except Exception as e:
            print(f"[DB] Could not link accounts: {e}")
    
    async def get_discord_user(self, discord_id: int) -> Optional[Dict]:
        """Get Discord user and their linked Roblox account"""
        try:
            if self.discord_users is not None:
                return self.discord_users.find_one({"discord_id": discord_id})
        except Exception as e:
            print(f"[DB] Could not get discord user: {e}")
        return None
    
    async def get_discord_user_by_roblox(self, roblox_user_id: int) -> Optional[Dict]:
        """Get Discord user by their linked Roblox account"""
        try:
            if self.discord_users:
                return self.discord_users.find_one({"roblox_user_id": roblox_user_id})
        except Exception as e:
            print(f"[DB] Could not get user by roblox: {e}")
        return None
    
    async def unlink_discord_from_roblox(self, discord_id: int):
        """Unlink a Discord user from their Roblox account"""
        try:
            if self.discord_users is not None:
                self.discord_users.delete_one({"discord_id": discord_id})
        except Exception as e:
            print(f"[DB] Could not unlink: {e}")
    
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
    
    async def get_all_pet_values(self, game: str = "PS99") -> Dict[str, int]:
        """Get all pet values for a specific game"""
        pets = self.pet_values.find({"game": game})
        return {pet["name"]: pet.get("value", 0) for pet in pets}
    
    def close(self):
        """Close database connection"""
        self.client.close()
