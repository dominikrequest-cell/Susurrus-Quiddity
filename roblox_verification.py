"""
Roblox account verification logic ported from PHP
Handles user lookup, verification code checking, and user metadata caching
"""

import httpx
import asyncio
from typing import Optional, Dict, Tuple
from database import Database
from datetime import datetime, timedelta


class RobloxVerification:
    """Handles Roblox user verification and metadata retrieval"""
    
    ROBLOX_API_BASE = "https://api.roblox.com"
    ROBLOX_USERS_API = "https://users.roblox.com/v1/users"
    ROBLOX_THUMBNAILS_API = "https://thumbnails.roblox.com/v1"
    
    def __init__(self, db: Database):
        self.db = db
        self.client = httpx.AsyncClient(timeout=10.0)
        self._cache = {}
    
    async def get_user_id(self, username: str) -> Optional[int]:
        """Get Roblox user ID from username, checking DB cache first"""
        # Check database cache
        cached_user = await self.db.get_user_by_username(username)
        if cached_user:
            return cached_user["user_id"]
        
        # Fetch from Roblox API if not cached
        user_info = await self._get_roblox_user_info(username)
        if user_info:
            # Cache in database
            await self.db.insert_or_update_user(
                user_id=user_info["Id"],
                username=user_info["Username"]
            )
            return user_info["Id"]
        
        return None
    
    async def get_username(self, user_id: int) -> Optional[str]:
        """Get Roblox username from user ID, checking DB cache first"""
        # Check database cache
        cached_user = await self.db.get_user_by_id(user_id)
        if cached_user:
            return cached_user["username"]
        
        # Fetch from Roblox API
        user_info = await self._get_roblox_user_by_id(user_id)
        if user_info:
            await self.db.insert_or_update_user(
                user_id=user_id,
                username=user_info["name"]
            )
            return user_info["name"]
        
        return None
    
    async def get_user_description(self, user_id: int, use_cache: bool = True) -> Optional[str]:
        """Get user's Roblox bio/description"""
        if use_cache:
            cached_desc = await self.db.get_user_description(user_id)
            if cached_desc:
                return cached_desc
        
        user_info = await self._get_roblox_user_by_id(user_id)
        if user_info and "description" in user_info:
            # Cache in database
            await self.db.update_user_description(user_id, user_info["description"])
            return user_info["description"]
        
        return None
    
    async def verify_code_in_description(self, user_id: int, code: str) -> bool:
        """Check if verification code exists in user's Roblox bio"""
        description = await self.get_user_description(user_id, use_cache=False)
        if description:
            return code in description
        return False
    
    async def get_user_thumbnail(self, user_id: int, size: str = "420x420", fresh: bool = False) -> Optional[str]:
        """Get user's avatar thumbnail, with caching and retry logic"""
        if not fresh:
            cached_thumb = await self.db.get_user_thumbnail(user_id)
            if cached_thumb:
                return cached_thumb
        
        try:
            response = await self.client.get(
                f"{self.ROBLOX_THUMBNAILS_API}/users/avatar-headshot",
                params={
                    "userIds": user_id,
                    "size": size,
                    "format": "Png",
                    "isCircular": "false"
                }
            )
            data = response.json()
            
            if "data" in data and len(data["data"]) > 0:
                if data["data"][0]["state"] == "Completed":
                    image_url = data["data"][0]["imageUrl"]
                    # Cache in database
                    await self.db.update_user_thumbnail(user_id, image_url)
                    return image_url
                else:
                    # Retry after delay if still processing
                    await asyncio.sleep(1)
                    return await self.get_user_thumbnail(user_id, size, fresh=True)
        except Exception as e:
            print(f"Error fetching thumbnail for user {user_id}: {e}")
        
        return None
    
    async def _get_roblox_user_info(self, username: str) -> Optional[Dict]:
        """Fetch user info from Roblox API by username"""
        try:
            response = await self.client.get(
                f"{self.ROBLOX_API_BASE}/users/get-by-username",
                params={"username": username}
            )
            data = response.json()
            if "Id" in data:
                return data
        except Exception as e:
            print(f"Error fetching user info for {username}: {e}")
        return None
    
    async def _get_roblox_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Fetch user info from Roblox API by user ID"""
        try:
            response = await self.client.get(f"{self.ROBLOX_USERS_API}/{user_id}")
            data = response.json()
            if "id" in data:
                return data
        except Exception as e:
            print(f"Error fetching user info for ID {user_id}: {e}")
        return None
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
