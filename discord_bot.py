"""
Discord bot for account verification, inventory management, and trading
Uses discord.py framework with slash commands
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import httpx
from datetime import datetime, timedelta
from typing import Optional

from database import Database
from roblox_verification import RobloxVerification
from security_manager import SecurityManager


# Initialize components
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

db = Database()
roblox = RobloxVerification(db)
security = SecurityManager(api_secret=os.getenv("API_SECRET", "default-secret-key"))

API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")
API_SECRET = os.getenv("API_SECRET", "")
# ============== Event Handlers ==============

@bot.event
async def on_ready():
    """Bot startup"""
    print(f"🤖 {bot.user} is ready!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
    # Start background tasks
    sync_inventory.start()


# ============== Verification Commands ==============

@bot.tree.command(name="verify", description="Verify your Roblox account and link it to Discord")
async def verify_account(interaction: discord.Interaction, roblox_username: str):
    """Verify your Roblox account and link it to Discord"""
    await interaction.response.defer()
    
    # Check if user already has a linked account
    existing_link = await db.get_discord_user(interaction.user.id)
    if existing_link:
        embed = discord.Embed(
            title="❌ Account Already Linked",
            description=f"Your Discord is already linked to **{existing_link['roblox_username']}** (ID: {existing_link['roblox_user_id']})\n\nUse `/unlink` to disconnect the current account first.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Validate username
    is_valid, error = security.is_valid_username(roblox_username)
    if not is_valid:
        embed = discord.Embed(
            title="❌ Invalid Username",
            description=error,
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Check if Roblox user exists
    user_id = await roblox.get_user_id(roblox_username)
    if not user_id:
        embed = discord.Embed(
            title="❌ User Not Found",
            description=f"Could not find Roblox user '{roblox_username}'",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Generate verification code
    code = security.generate_verification_code()
    
    # Create DM embed with instructions
    embed = discord.Embed(
        title="🔐 Account Verification",
        description="To verify your Roblox account, follow these steps:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="1️⃣ Copy this code",
        value=f"```{code}```",
        inline=False
    )
    embed.add_field(
        name="2️⃣ Put it in your Roblox bio",
        value="Go to your Roblox profile and add this code to your About section",
        inline=False
    )
    embed.add_field(
        name="3️⃣ Confirm verification",
        value=f"Once done, use `/verify-confirm` and enter: {roblox_username}",
        inline=False
    )
    embed.set_footer(text="Code expires in 10 minutes")
    
    # Send DM
    try:
        await interaction.user.send(embed=embed)
        await interaction.followup.send(f"✅ Check your DMs! You'll need to add a code to your Roblox bio to verify.")
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Cannot DM",
            description="Please enable DMs from server members",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Store code temporarily
    bot.pending_verifications = getattr(bot, 'pending_verifications', {})
    bot.pending_verifications[interaction.user.id] = {
        "code": code,
        "username": roblox_username,
        "user_id": user_id,
        "expires_at": datetime.utcnow() + timedelta(minutes=10)
    }


@bot.tree.command(name="unlink", description="Unlink your Roblox account from Discord")
async def unlink_account(interaction: discord.Interaction):
    """Unlink your Roblox account from Discord"""
    await interaction.response.defer()
    
    # Check if user has a linked account
    discord_user = await db.get_discord_user(interaction.user.id)
    if not discord_user:
        embed = discord.Embed(
            title="❌ Not Linked",
            description="Your Discord account is not linked to any Roblox account.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Remove the link from database
    await db.unlink_discord_from_roblox(interaction.user.id)
    
    embed = discord.Embed(
        title="✅ Account Unlinked",
        description=f"Your Roblox account **{discord_user['roblox_username']}** has been unlinked.\n\nYou can now verify a different account with `/verify`.",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="verify-confirm", description="Confirm verification by checking if code is in your Roblox bio")
async def verify_confirm(interaction: discord.Interaction, roblox_username: str):
    """Confirm verification by checking if code is in your Roblox bio"""
    await interaction.response.defer()
    
    # Get pending verification
    pending = getattr(bot, 'pending_verifications', {})
    if interaction.user.id not in pending:
        embed = discord.Embed(
            title="❌ No Pending Verification",
            description="Run `/verify` first",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    verification = pending[interaction.user.id]
    
    # Check if expired
    if datetime.utcnow() > verification["expires_at"]:
        del pending[interaction.user.id]
        embed = discord.Embed(
            title="❌ Verification Expired",
            description="Please run `/verify` again",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Check if code is in user's bio
    code = verification["code"]
    user_id = verification["user_id"]
    username = verification["username"]
    
    is_verified = await roblox.verify_code_in_description(user_id, code)
    
    if not is_verified:
        embed = discord.Embed(
            title="❌ Code Not Found",
            description=f"Could not find the verification code in your Roblox bio.\nMake sure you added:\n```{code}```",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Link accounts
    await db.link_discord_to_roblox(
        discord_id=interaction.user.id,
        roblox_user_id=user_id,
        discord_username=str(interaction.user)
    )
    
    # Clean up
    del pending[interaction.user.id]
    
    # Get avatar thumbnail
    thumbnail = await roblox.get_user_thumbnail(user_id, fresh=True)
    
    # Success embed
    embed = discord.Embed(
        title="✅ Verification Successful!",
        description=f"Your Roblox account '{username}' is now linked to your Discord!",
        color=discord.Color.green()
    )
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    embed.add_field(
        name="Next Steps",
        value="You can now use `/deposit` and `/withdraw` commands!",
        inline=False
    )
    await interaction.followup.send(embed=embed)


# ============== Inventory Commands ==============

@bot.tree.command(name="inventory", description="Show your pet inventory")
async def show_inventory(interaction: discord.Interaction):
    """Show your pet inventory"""
    await interaction.response.defer()
    
    # Get Discord user link
    discord_user = await db.get_discord_user(interaction.user.id)
    if not discord_user:
        embed = discord.Embed(
            title="❌ Not Verified",
            description="Please verify your account first with `/verify`",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Get inventory
    inventory = await db.get_inventory(interaction.user.id)
    gems = await db.get_user_gem_balance(interaction.user.id)
    
    # Build inventory embed
    embed = discord.Embed(
        title="🎮 Your Inventory",
        description=f"Linked to: **{discord_user['roblox_user_id']}**",
        color=discord.Color.purple()
    )
    
    if inventory:
        for item in inventory:
            embed.add_field(
                name=item["pet_name"],
                value=f"Quantity: {item['quantity']}",
                inline=True
            )
    else:
        embed.add_field(
            name="No Pets",
            value="You don't have any pets yet. Deposit some!",
            inline=False
        )
    
    embed.add_field(
        name="💎 Gems",
        value=f"{gems:,}",
        inline=False
    )
    
    embed.set_footer(text=f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="balance", description="Check your gem balance")
async def check_balance(interaction: discord.Interaction):
    """Check your gem balance"""
    await interaction.response.defer()
    
    discord_user = await db.get_discord_user(interaction.user.id)
    if not discord_user:
        embed = discord.Embed(
            title="❌ Not Verified",
            description="Please verify your account first",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    gems = await db.get_user_gem_balance(interaction.user.id)
    
    embed = discord.Embed(
        title="💎 Your Gem Balance",
        description=f"{gems:,} gems",
        color=discord.Color.gold()
    )
    await interaction.followup.send(embed=embed)


# ============== Trade Commands ==============

@bot.tree.command(name="deposit", description="Start a deposit (send pets/gems to bot)")
async def initiate_deposit(interaction: discord.Interaction):
    """Start a deposit (send pets/gems to bot)"""
    await interaction.response.defer()
    
    discord_user = await db.get_discord_user(interaction.user.id)
    if not discord_user:
        embed = discord.Embed(
            title="❌ Not Verified",
            description="Please verify your account first",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="💰 Deposit Instructions",
        description="Follow these steps to deposit pets and gems:",
        color=discord.Color.green()
    )
    embed.add_field(
        name="1️⃣ Join the Game",
        value="Go to the Roblox game and join",
        inline=False
    )
    embed.add_field(
        name="2️⃣ Trade the Bot",
        value="Send a trade request to the bot account with your pets/gems",
        inline=False
    )
    embed.add_field(
        name="3️⃣ Complete Trade",
        value="Accept the trade. Your inventory will update automatically!",
        inline=False
    )
    embed.add_field(
        name="⚠️ Deposit Rules",
        value="• Only Huge and Titanic pets\n• Minimum 50M gems per deposit\n• Maximum 10B gems per deposit\n• Gems must be in 50M blocks",
        inline=False
    )
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="withdraw", description="Start a withdrawal (get pets/gems from bot)")
async def initiate_withdraw(interaction: discord.Interaction):
    """Start a withdrawal (get pets/gems from bot)"""
    await interaction.response.defer()
    
    discord_user = await db.get_discord_user(interaction.user.id)
    if not discord_user:
        embed = discord.Embed(
            title="❌ Not Verified",
            description="Please verify your account first",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="🎁 Withdrawal Instructions",
        description="Follow these steps to withdraw pets:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="1️⃣ Join the Game",
        value="Go to the Roblox game and join",
        inline=False
    )
    embed.add_field(
        name="2️⃣ Send Trade",
        value="Send a trade request to the bot",
        inline=False
    )
    embed.add_field(
        name="3️⃣ Complete Trade",
        value="The bot will send your requested pets. Accept to complete!",
        inline=False
    )
    await interaction.followup.send(embed=embed)


# ============== Transaction History ==============

@bot.tree.command(name="history", description="Show your transaction history")
async def transaction_history(interaction: discord.Interaction, limit: int = 10):
    """Show your transaction history"""
    await interaction.response.defer()
    
    discord_user = await db.get_discord_user(interaction.user.id)
    if not discord_user:
        embed = discord.Embed(
            title="❌ Not Verified",
            description="Please verify your account first",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    transactions = await db.get_user_transactions(interaction.user.id, limit)
    
    embed = discord.Embed(
        title="📜 Transaction History",
        color=discord.Color.blurple()
    )
    
    if not transactions:
        embed.add_field(
            name="No Transactions",
            value="You haven't made any trades yet",
            inline=False
        )
    else:
        for tx in transactions:
            status_emoji = "✅" if tx.get("status") == "completed" else "⏳"
            embed.add_field(
                name=f"{status_emoji} {tx['type'].upper()}",
                value=f"Pets: {len(tx.get('pets', []))} | Gems: {tx.get('gems', 0):,}\n{tx['created_at']}",
                inline=False
            )
    
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    """Show all available commands"""
    await interaction.response.defer()
    
    embed = discord.Embed(
        title="🤖 Pet Trading Bot",
        description="Slash commands for managing your Roblox pet inventory",
        color=discord.Color.blurple()
    )
    
    embed.add_field(
        name="🔐 Verification",
        value="`/verify` - Link your Roblox account\n`/verify-confirm` - Confirm verification\n`/unlink` - Unlink your Roblox account",
        inline=False
    )
    
    embed.add_field(
        name="📊 Inventory",
        value="`/inventory` - Show your pets and gems\n`/balance` - Check gem balance",
        inline=False
    )
    
    embed.add_field(
        name="💱 Trading",
        value="`/deposit` - Deposit pets/gems to bot\n`/withdraw` - Withdraw pets from bot",
        inline=False
    )
    
    embed.add_field(
        name="📜 History",
        value="`/history [limit]` - Show transaction history",
        inline=False
    )
    
    await interaction.followup.send(embed=embed)


# ============== Background Tasks ==============

@tasks.loop(minutes=5)
async def sync_inventory():
    """Periodically sync inventory from trades"""
    try:
        print("Syncing inventory...")
    except Exception as e:
        print(f"Inventory sync error: {e}")


# Error handler
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors"""
    embed = discord.Embed(
        title="❌ Error",
        description=str(error),
        color=discord.Color.red()
    )
    
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable not set")
    bot.run(token)
