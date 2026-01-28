"""
Import supported pets from petsimulatorvalues.com into the database
"""
import asyncio
import httpx
from bs4 import BeautifulSoup
from database import Database
import os
from dotenv import load_dotenv

load_dotenv()

async def fetch_pet_data():
    """Fetch pet data from petsimulatorvalues.com"""
    url = "https://petsimulatorvalues.com"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

async def parse_pets(html_content):
    """Parse pet names from HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    pets = []
    
    # Look for Huge and Titanic pets
    # The site structure may vary, so we'll look for common patterns
    pet_elements = soup.find_all(['div', 'span', 'td'], class_=lambda x: x and ('pet' in x.lower() or 'item' in x.lower()))
    
    for element in pet_elements:
        text = element.get_text(strip=True)
        
        # Look for "Huge" or "Titanic" pets
        if ('Huge' in text or 'Titanic' in text) and len(text) < 100:
            # Clean up the text
            pet_name = text.strip()
            
            # Generate variants (Normal, Golden, Rainbow, Shiny combinations)
            variants = [
                pet_name,  # Normal
                f"Golden {pet_name}",
                f"Rainbow {pet_name}",
                f"Shiny {pet_name}",
                f"Shiny Golden {pet_name}",
                f"Shiny Rainbow {pet_name}"
            ]
            
            pets.extend(variants)
    
    # Remove duplicates
    pets = list(set(pets))
    return pets

async def import_all_huges_titanics():
    """Import all common Huge and Titanic pets"""
    # Common Huge pets from PS99
    huge_pets = [
        "Huge Cat",
        "Huge Corgi",
        "Huge Dog",
        "Huge Dalmation",
        "Huge Dragon",
        "Huge Hell Rock",
        "Huge Pumpkin Cat",
        "Huge Cupcake",
        "Huge Santa Paws",
        "Huge Festive Cat",
        "Huge Festive Dog",
        "Huge Happy Rock",
        "Huge Cyberpunk Cat",
        "Huge Cyberpunk Dog",
        "Huge Unicorn",
        "Huge Pegasus",
        "Huge Balloon Cat",
        "Huge Balloon Dog",
        "Huge Axolotl",
        "Huge Easter Cat",
        "Huge Otter",
        "Huge Lucky Cat",
        "Huge Lucky Dog",
        "Huge Storm Wolf",
        "Huge Storm Agony",
        "Huge Kawaii Cat",
        "Huge Punksky",
        "Huge Cartoon Cat",
        "Huge Pixel Cat",
        "Huge Pixel Demon",
        "Huge Summer Cat",
        "Huge Summer Monkey",
        "Huge Sailor Cat",
        "Huge Tiki Dominus",
        "Huge Meebo in a Spaceship",
        "Huge Gargoyle Dragon",
        "Huge Pterodactyl",
        "Huge Hell Cat",
        "Huge Steampunk Octopus",
        "Huge Evolved Bat",
        "Huge Vampire Bat",
    ]
    
    # Common Titanic pets
    titanic_pets = [
        "Titanic Cat",
        "Titanic Corgi",
        "Titanic Dog",
        "Titanic Pumpkin Cat",
        "Titanic Holiday Cat",
        "Titanic Cyberpunk Dragon",
        "Titanic Unicorn",
        "Titanic Balloon Cat",
        "Titanic Storm Agony",
        "Titanic Pixel Cat",
        "Titanic Summer Monkey",
        "Titanic Tiki Dominus",
        "Titanic Gargoyle Dragon",
        "Titanic Steampunk Octopus",
    ]
    
    all_pets = []
    
    # Generate all variants for each pet
    for pet in huge_pets + titanic_pets:
        variants = [
            pet,  # Normal
            f"Golden {pet}",
            f"Rainbow {pet}",
            f"Shiny {pet}",
            f"Shiny Golden {pet}",
            f"Shiny Rainbow {pet}"
        ]
        all_pets.extend(variants)
    
    return all_pets

async def main():
    print("Connecting to database...")
    db = Database()
    
    # Try to fetch from website first
    print("Attempting to fetch pet data from petsimulatorvalues.com...")
    html = await fetch_pet_data()
    
    pets = []
    if html:
        pets = await parse_pets(html)
        print(f"Found {len(pets)} pets from website")
    
    # If website scraping didn't work or returned few pets, use hardcoded list
    if len(pets) < 50:
        print("Using comprehensive hardcoded pet list...")
        pets = await import_all_huges_titanics()
        print(f"Using {len(pets)} pets from hardcoded list")
    
    if not pets:
        print("No pets found to import!")
        return
    
    # Import pets into database
    print(f"\nImporting {len(pets)} pets into database...")
    
    try:
        # Clear existing pets for PS99
        result = db.pet_values.delete_many({"game": "PS99"})
        print(f"Cleared {result.deleted_count} existing PS99 pets")
        
        # Insert new pets
        pet_documents = []
        for pet_name in pets:
            pet_documents.append({
                "name": pet_name,
                "game": "PS99",
                "value": 0,  # You can update values later
                "exists": True,
                "rap": 0
            })
        
        if pet_documents:
            result = db.pet_values.insert_many(pet_documents)
            print(f"Successfully imported {len(result.inserted_ids)} pets!")
            
            # Show some examples
            print("\nExample pets imported:")
            for i, pet in enumerate(pets[:10]):
                print(f"  - {pet}")
            if len(pets) > 10:
                print(f"  ... and {len(pets) - 10} more")
        
    except Exception as e:
        print(f"Error importing pets: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
