#!/usr/bin/env python
import subprocess
import sys

# Upgrade pip
subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

# Install requirements
subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", "requirements.txt"])

print("Dependencies installed successfully!")
