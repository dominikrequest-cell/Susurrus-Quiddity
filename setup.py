from setuptools import setup

setup(
    name="pet-trading-bot",
    version="1.0.0",
    py_modules=["api", "discord_bot", "database", "config", "security_manager", "roblox_verification", "trade_processor"],
    install_requires=[
        # Discord
        "discord.py==2.3.2",
        # API
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "pydantic==2.5.0",
        # Database
        "pymongo==4.6.0",
        # HTTP
        "httpx==0.25.2",
        "requests==2.31.0",
        # Security
        "cryptography==41.0.7",
        # Environment
        "python-dotenv==1.0.0",
        # Utilities
        "cloudscraper==1.2.71",
        "beautifulsoup4==4.12.2",
        "html5lib==1.1",
        # Logging
        "python-json-logger==2.0.7",
        # Development
        "pytest==7.4.3",
        "pytest-asyncio==0.21.1",
        "black==23.12.0",
        "flake8==6.1.0",
    ],
)
