# Production Setup Script for SMS Proxy Service

echo "🚀 SMS Proxy Service - Production Setup"
echo "======================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating environment configuration file (.env)..."
    cat > .env << 'EOF'
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# SMS Provider Configuration  
SMSPOOL_API_KEY=your_smspool_api_key_here

# Admin Configuration (comma-separated user IDs)
ADMIN_USER_IDS=your_user_id_here

# Database Configuration
DATABASE_PATH=./data/database.json

# Optional: Development/Testing Configuration
ENVIRONMENT=production
ALLOW_MOCK=false
LOG_LEVEL=INFO
EOF
    echo "✅ Created .env file with template configuration"
    echo ""
    echo "🔧 IMPORTANT: Please edit .env file with your actual values:"
    echo "   1. Get your Telegram bot token from @BotFather"
    echo "   2. Get your SMSPool API key from smspool.net"
    echo "   3. Add your Telegram user ID as admin"
    echo ""
    echo "💡 To find your Telegram user ID, message your bot with /start"
    echo ""
else
    echo "✅ Environment file (.env) already exists"
fi

# Create data directory
mkdir -p data
mkdir -p logs

echo "📁 Created required directories:"
echo "   - data/ (for database)"  
echo "   - logs/ (for logging)"

# Check Python dependencies
echo ""
echo "🐍 Checking Python dependencies..."
if python3 -c "import telegram, aiohttp, tinydb" 2>/dev/null; then
    echo "✅ All required Python packages are installed"
else
    echo "📦 Installing required packages..."
    pip3 install -r requirements.txt
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "   1. Edit .env file with your configuration"
echo "   2. Run: python3 main.py"
echo "   3. Test your bot on Telegram"
echo ""
echo "🔧 For testing/development, you can enable mock mode by setting:"
echo "   ALLOW_MOCK=true in .env file"
