# Quick Start Script for Ring4 Bot

echo "🚀 Ring4 Bot Quick Start"
echo "========================"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the bot directory."
    exit 1
fi

# Check if .env exists and is configured
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Please create it from .env.example"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found. Please install Python 3.8+"
    exit 1
fi

# Check dependencies
echo "🔍 Checking dependencies..."
if ! python3 -c "import telegram, aiohttp, tinydb, dotenv" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    python3 -m pip install -r requirements.txt
else
    echo "✅ Dependencies OK"
fi

# Run validation
echo "🧪 Running validation tests..."
if python3 validate_bot.py; then
    echo ""
    echo "🎉 Validation passed! Starting Ring4 Bot..."
    echo "📱 Bot will start in 3 seconds..."
    echo "⌨️  Press Ctrl+C to stop"
    sleep 3
    
    # Start the bot
    python3 main.py
else
    echo "❌ Validation failed. Please check configuration."
    exit 1
fi
