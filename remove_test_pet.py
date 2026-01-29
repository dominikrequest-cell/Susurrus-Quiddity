"""Quick script to remove a Huge Red Fox from user's inventory"""
import os
from dotenv import load_dotenv

load_dotenv()

from database import Database

def main():
    db = Database()
    
    if not db.db_available:
        print("Database not available!")
        return
    
    # Your Roblox user ID: 3858312330
    user = db.discord_users.find_one({"roblox_user_id": 3858312330})
    if not user:
        user = db.discord_users.find_one({"roblox_user_id_str": "3858312330"})
    
    if not user:
        print("User not found!")
        return
    
    discord_id = user['discord_id']
    print(f"Found Discord user: {discord_id} -> {user.get('roblox_username')}")
    
    # Remove Huge Red Fox from inventory
    db.inventory.update_one(
        {"discord_id": discord_id, "pet_name": "Huge Red Fox"},
        {"$inc": {"quantity": -1}}
    )
    
    # Delete if quantity reaches 0
    db.inventory.delete_one({"discord_id": discord_id, "pet_name": "Huge Red Fox", "quantity": {"$lte": 0}})
    
    print("✅ Removed 1x Huge Red Fox from your inventory!")
    
    # Show current inventory
    inventory = list(db.inventory.find({"discord_id": discord_id}))
    print(f"\nYour inventory ({len(inventory)} unique pets):")
    for item in inventory:
        print(f"  - {item['pet_name']} x{item['quantity']}")

if __name__ == "__main__":
    main()
