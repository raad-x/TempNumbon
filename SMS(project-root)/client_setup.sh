#!/bin/bash
# =============================================================================
# Ring4 SMS Bot - Client Setup Script
# =============================================================================
# This script helps new users set up the bot quickly and correctly
# =============================================================================

echo "🚀 Ring4 SMS Bot - Client Setup"
echo "================================"
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ Please don't run this script as root!"
   exit 1
fi

# Check Python installation
echo "🔍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3.8 or higher and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $PYTHON_VERSION"

# Check pip installation
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    exit 1
fi

echo "✅ Found pip3"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📦 Installing requirements..."
pip install -r requirements.txt
echo "✅ Requirements installed"

# Create .env from template if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env configuration file..."
    cp .env.example .env
    echo "✅ .env file created from template"
    echo ""
    echo "🔧 IMPORTANT: Please edit .env file with your actual values:"
    echo "   - BOT_TOKEN (from @BotFather)"
    echo "   - SMSPOOL_API_KEY (from SMSPool)"
    echo "   - ADMIN_USER_IDS (your Telegram user ID)"
    echo ""
    read -p "Press Enter after you've configured .env..."
else
    echo "✅ .env file already exists"
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p data/backups logs
echo "✅ Directories created"

# Set permissions
echo "🔒 Setting permissions..."
chmod +x start_bot.sh restart_bot.sh
echo "✅ Permissions set"

# Test configuration
echo "🧪 Testing configuration..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from src.config import *
    print('✅ Configuration loaded successfully')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Configuration test passed"
else
    echo "❌ Configuration test failed. Please check your .env file."
    exit 1
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Start the bot: ./start_bot.sh"
echo "2. Check status: tail -f logs/ring4_bot.log"
echo "3. Stop the bot: ./restart_bot.sh stop"
echo ""
echo "👑 Admin commands available in Telegram:"
echo "- /db_status - Check database protection"
echo "- /admin - Admin dashboard"
echo "- /help - Full command list"
echo ""
echo "🛡️ Your database is automatically protected with 3-day backups!"
echo "✅ Ready for production use!"
