#!/bin/bash

# Ring4 Bot Cleanup and Restart Script
# This script ensures clean bot startup by eliminating conflicts

echo "🧹 Ring4 Bot Cleanup & Restart Script"
echo "====================================="

# Step 1: Kill any existing bot processes
echo "🔍 Checking for existing bot processes..."
if pgrep -f "python.*main.py" > /dev/null; then
    echo "⚠️  Found existing bot processes. Stopping them..."
    pkill -f "python.*main.py"
    sleep 3
    
    # Force kill if still running
    if pgrep -f "python.*main.py" > /dev/null; then
        echo "💀 Force killing stubborn processes..."
        pkill -9 -f "python.*main.py"
        sleep 2
    fi
    echo "✅ Bot processes stopped"
else
    echo "✅ No existing bot processes found"
fi

# Step 2: Clear Telegram webhook
echo "🔄 Clearing Telegram webhook..."
python3 clear_webhook.py
sleep 2

# Step 3: Wait a moment for Telegram to process
echo "⏱️  Waiting for Telegram API to clear conflicts..."
sleep 5

# Step 4: Start the bot
echo "🚀 Starting Ring4 Bot..."
python3 main.py
