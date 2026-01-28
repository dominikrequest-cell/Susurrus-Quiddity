"""
Discord bot for account verification, inventory management, and trading
Uses discord.py framework
"""

import discord
from discord.ext import commands, tasks
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
    # Start background tasks
    sync_inventory.start()


# ============== Verification Commands ==============

@bot.command(name="verify")
async def verify_account(ctx, roblox_username: str):
    """
    Verify your Roblox account and link it to Discord
    Usage: !verify YourRobloxUsername
    """
    # Validate username
    is_valid, error = security.is_valid_username(roblox_username)
    if not is_valid:
        embed = discord.Embed(
            title="❌ Invalid Username",
            description=error,
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Check if Roblox user exists
    user_id = await roblox.get_user_id(roblox_username)
    if not user_id:
        embed = discord.Embed(
            title="❌ User Not Found",
            description=f"Could not find Roblox user '{roblox_username}'",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
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
        value=f"Once done, run: `!verify-confirm {roblox_username}`",
        inline=False
    )
    embed.set_footer(text="Code expires in 10 minutes")
    
    # Send DM
    try:
        await ctx.author.send(embed=embed)
        await ctx.send(f"✅ Check your DMs! You'll need to add a code to your Roblox bio to verify.")
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Cannot DM",
            description="Please enable DMs from server members",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Store code temporarily (in production, use Redis)
    # For now, store in memory cache with TTL
    ctx.bot.pending_verifications = getattr(ctx.bot, 'pending_verifications', {})
    ctx.bot.pending_verifications[ctx.author.id] = {
        "code": code,
        "username": roblox_username,
        "user_id": user_id,
        "expires_at": datetime.utcnow() + timedelta(minutes=10)
    }


@bot.command(name="verify-confirm")
async def verify_confirm(ctx, roblox_username: str):
    """
    Confirm verification by checking if code is in your Roblox bio
    Usage: !verify-confirm YourRobloxUsername
    """
    # Get pending verification
    pending = getattr(ctx.bot, 'pending_verifications', {})
    if ctx.author.id not in pending:
        embed = discord.Embed(
            title="❌ No Pending Verification",
            description="Run `!verify <username>` first",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    verification = pending[ctx.author.id]
    
    # Check if expired
    if datetime.utcnow() > verification["expires_at"]:
        del pending[ctx.author.id]
        embed = discord.Embed(
            title="❌ Verification Expired",
            description="Please run `!verify` again",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
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
        await ctx.send(embed=embed)
        return
    
    # Link accounts
    await db.link_discord_to_roblox(
        discord_id=ctx.author.id,
        roblox_user_id=user_id,
        discord_username=str(ctx.author)
    )
    
    # Clean up
    del pending[ctx.author.id]
    
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
        value="You can now deposit/withdraw pets using `/deposit` and `/withdraw` commands!",
        inline=False
    )
    await ctx.send(embed=embed)


# ============== Inventory Commands ==============

@bot.command(name="inventory")
async def show_inventory(ctx):
    """
    Show your pet inventory
    Usage: !inventory
    """
    # Get Discord user link
    discord_user = await db.get_discord_user(ctx.author.id)
    if not discord_user:
        embed = discord.Embed(
            title="❌ Not Verified",
            description="Please verify your account first with `!verify <username>`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Get inventory
    inventory = await db.get_inventory(ctx.author.id)
    gems = await db.get_user_gem_balance(ctx.author.id)
    
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
    await ctx.send(embed=embed)


@bot.command(name="balance")
async def check_balance(ctx):
    """
    Check your gem balance
    Usage: !balance
    """
    discord_user = await db.get_discord_user(ctx.author.id)
    if not discord_user:
        embed = discord.Embed(
            title="❌ Not Verified",
            description="Please verify your account first",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    gems = await db.get_user_gem_balance(ctx.author.id)
    
    embed = discord.Embed(
        title="💎 Your Gem Balance",
        description=f"{gems:,} gems",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


# ============== Trade Commands ==============

@bot.command(name="deposit")
async def initiate_deposit(ctx):
    """
    Start a deposit (send pets/gems to bot)
    You'll need to join the Roblox game and trade the bot
    Usage: !deposit
    """
    discord_user = await db.get_discord_user(ctx.author.id)
    if not discord_user:
        embed = discord.Embed(
            title="❌ Not Verified",
            description="Please verify your account first",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
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
    await ctx.send(embed=embed)


@bot.command(name="withdraw")
async def initiate_withdraw(ctx):
    """
    Start a withdrawal (get pets/gems from bot)
    Usage: !withdraw <pet1> <pet2> ...
    """
    discord_user = await db.get_discord_user(ctx.author.id)
    if not discord_user:
        embed = discord.Embed(
            title="❌ Not Verified",
            description="Please verify your account first",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
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
    await ctx.send(embed=embed)


# ============== Transaction History ==============

@bot.command(name="history")
async def transaction_history(ctx, limit: int = 10):
    """
    Show your transaction history
    Usage: !history [limit]
    """
    discord_user = await db.get_discord_user(ctx.author.id)
    if not discord_user:
        embed = discord.Embed(
            title="❌ Not Verified",
            description="Please verify your account first",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    transactions = await db.get_user_transactions(ctx.author.id, limit)
    
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
    
    await ctx.send(embed=embed)


# ============== Background Tasks ==============

@tasks.loop(minutes=5)
async def sync_inventory():
    """Periodically sync inventory from trades"""
    # In production, would fetch completed trades from API
    # and update Discord user inventories
    print("Syncing inventory...")


@bot.command(name="help")
async def help_command(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🤖 Pet Trading Bot",
        description="Commands for managing your Roblox pet inventory",
        color=discord.Color.blurple()
    )
    
    embed.add_field(
        name="🔐 Verification",
        value="`!verify <username>` - Link your Roblox account\n`!verify-confirm <username>` - Confirm verification",
        inline=False
    )
    
    embed.add_field(
        name="📊 Inventory",
        value="`!inventory` - Show your pets and gems\n`!balance` - Check gem balance",
        inline=False
    )
    
    embed.add_field(
        name="💱 Trading",
        value="`!deposit` - Deposit pets/gems to bot\n`!withdraw` - Withdraw pets from bot",
        inline=False
    )
    
    embed.add_field(
        name="📜 History",
        value="`!history [limit]` - Show transaction history",
        inline=False
    )
    
    await ctx.send(embed=embed)


# Error handler
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    embed = discord.Embed(
        title="❌ Error",
        description=str(error),
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable not set")
    bot.run(token)
