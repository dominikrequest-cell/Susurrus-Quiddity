"""Quick script to add a Huge Red Fox to user's inventory for testing"""
import os
from dotenv import load_dotenv

load_dotenv()

from database import Database

def main():
    db = Database()
    
    if not db.db_available:
        print("Database not available!")
        return
    
    # Your Roblox user ID from earlier: 3858312330
    # Need to find your Discord ID from the linked accounts
    
    user = db.discord_users.find_one({"roblox_user_id": 3858312330})
    if not user:
        # Try string version
        user = db.discord_users.find_one({"roblox_user_id_str": "3858312330"})
    
    if not user:
        print("User not found! Make sure you're verified.")
        print("Checking all users...")
        for u in db.discord_users.find():
            print(f"  Discord: {u.get('discord_id')}, Roblox: {u.get('roblox_user_id')}")
        return
    
    discord_id = user['discord_id']
    print(f"Found Discord user: {discord_id} -> {user.get('roblox_username')}")
    
    # Add Huge Red Fox to inventory
    db.inventory.update_one(
        {"discord_id": discord_id, "pet_name": "Huge Red Fox"},
        {
            "$inc": {"quantity": 1},
            "$set": {
                "pet_data": {
                    "type": "Normal",
                    "shiny": False,
                    "game": "PS99"
                },
                "updated_at": None
            },
            "$setOnInsert": {
                "discord_id": discord_id,
                "pet_name": "Huge Red Fox",
                "created_at": None
            }
        },
        upsert=True
    )
    
    print("✅ Added 1x Huge Red Fox to your inventory!")
    
    # Show current inventory
    inventory = list(db.inventory.find({"discord_id": discord_id}))
    print(f"\nYour inventory ({len(inventory)} unique pets):")
    for item in inventory:
        print(f"  - {item['pet_name']} x{item['quantity']}")

if __name__ == "__main__":
    main()
