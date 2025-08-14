"""
Ring4 US-Only SMS Verification Bot - WITH PAYMENT WORKFLOW
Production-ready Telegram bot with payment approval system.
"""

import os
import sys
import logging
import asyncio
import re
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from tinydb import TinyDB, Query
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import configuration manager
try:
    from src.config import Config, ConfigurationManager
    logger = logging.getLogger(__name__)
    logger.info("✅ Configuration system loaded successfully")
except ImportError as config_error:
    print(f"❌ Failed to load configuration system: {config_error}")
    sys.exit(1)

SMSPoolAPI = None
WalletSystem = None
WALLET_SYSTEM_AVAILABLE = False

# Try to import wallet system and API modules
try:
    # Primary import strategy: from src package
    from src.smspool_api import SMSPoolAPI
    from src.wallet_system import WalletSystem
    WALLET_SYSTEM_AVAILABLE = True
    print("✅ Wallet system and API modules loaded from src package")
except ImportError as src_error:
    try:
        # Fallback strategy: direct imports
        from src.smspool_api import SMSPoolAPI
        from src.wallet_system import WalletSystem
        WALLET_SYSTEM_AVAILABLE = True
        print("✅ Wallet system and API modules loaded directly")
    except ImportError as direct_error:
        try:
            # Fallback strategy 2: absolute imports with current directory
            sys.path.insert(0, os.path.dirname(__file__))
            from src.smspool_api import SMSPoolAPI
            from src.wallet_system import WalletSystem
            WALLET_SYSTEM_AVAILABLE = True
            print("✅ Wallet system and API modules loaded with absolute path")
        except ImportError as abs_error:
            # Final fallback: create minimal mock classes to prevent crashes
            WALLET_SYSTEM_AVAILABLE = False
            print("⚠️ Wallet system modules not found:")
            print(f"   - src package error: {src_error}")
            print(f"   - direct import error: {direct_error}")
            print(f"   - absolute path error: {abs_error}")
            print("⚠️ Running with limited functionality - mock classes will be used")
            print(f"   - direct import error: {direct_error}")
            print(f"   - absolute path error: {abs_error}")
            print("📝 Running in limited mode - wallet functionality disabled")

            # Create minimal fallback classes to prevent AttributeError
            class MockWalletSystem:
                def __init__(self, database):
                    self.db = database
                    self.MIN_DEPOSIT_USD = 5.00
                    self.MAX_DEPOSIT_USD = 1000.00
                    # Add mock table attributes
                    self.deposits_table = None

                def get_user_balance(self, user_id):
                    """Mock implementation - always returns 0.00"""
                    _ = user_id  # Acknowledge unused parameter
                    return 0.00

                def has_sufficient_balance(self, user_id, amount):
                    """Mock implementation - always returns False"""
                    _ = user_id, amount  # Acknowledge unused parameters
                    return False

                def deduct_balance(self, user_id, amount, description, order_id=None):
                    """Mock implementation - always returns False"""
                    _ = user_id, amount, description, order_id  # Acknowledge unused parameters
                    return False

                def add_balance(self, user_id, amount, description, transaction_type='deposit'):
                    """Mock implementation - always returns False"""
                    _ = user_id, amount, description, transaction_type  # Acknowledge unused parameters
                    return False

                def process_service_purchase(self, user_id, service_price, service_name, order_id):
                    """Mock implementation - always returns False"""
                    _ = user_id, service_price, service_name, order_id  # Acknowledge unused parameters
                    return False

                def process_refund(self, user_id, refund_amount, order_id, reason):
                    """Mock implementation - always returns False"""
                    _ = user_id, refund_amount, order_id, reason  # Acknowledge unused parameters
                    return False

                def get_wallet_summary(self, user_id):
                    """Mock implementation - returns empty summary"""
                    _ = user_id  # Acknowledge unused parameter
                    return {
                        'balance': 0.00,
                        'total_deposited': 0.00,
                        'total_spent': 0.00,
                        'total_refunded': 0.00,
                        'recent_transactions': []
                    }

                def create_deposit_request(self, user_id, amount, binance_wallet):
                    """Mock implementation - returns deposit request structure"""
                    return {
                        'deposit_id': f'DEP_{user_id}_{int(datetime.now().timestamp())}',
                        'amount': amount,
                        'instructions': [
                            "*💰 Wallet Deposit Request*",
                            f"*Amount:* ${amount:.2f}",
                            f"*Wallet:* `{binance_wallet}`",
                            "",
                            f"⚠️ *IMPORTANT:* Send exactly ${amount:.2f}",
                            f"Include your user ID: {user_id} in transaction memo"
                        ]
                    }

                def get_pending_deposits(self):
                    """Mock implementation - returns empty list"""
                    return []

                def approve_deposit(self, deposit_id, admin_id):
                    """Mock implementation - always returns False"""
                    _ = deposit_id, admin_id  # Acknowledge unused parameters
                    return False

                def get_deposit_status(self, deposit_id):
                    """Mock implementation - returns None"""
                    _ = deposit_id  # Acknowledge unused parameter
                    return None

                def get_transaction_history(self, user_id, limit=20):
                    """Mock implementation - returns empty list"""
                    _ = user_id, limit  # Acknowledge unused parameters
                    return []

            class MockSMSPoolAPI:
                def __init__(self, api_key):
                    self.api_key = api_key

                async def purchase_ring4_number(self, *args, **kwargs):
                    """Mock implementation - returns failure response"""
                    _ = args, kwargs  # Acknowledge unused parameters
                    return {'success': False, 'message': 'API not available'}

                async def get_order_status(self, *args, **kwargs):
                    """Mock implementation - returns failure response"""
                    _ = args, kwargs  # Acknowledge unused parameters
                    return {'success': False, 'message': 'API not available'}

                async def cancel_order(self, *args, **kwargs):
                    """Mock implementation - returns failure response"""
                    _ = args, kwargs  # Acknowledge unused parameters
                    return {'success': False, 'message': 'API not available'}

                async def check_service_availability(self, *args, **kwargs):
                    """Mock implementation - returns failure response"""
                    _ = args, kwargs  # Acknowledge unused parameters
                    return {'success': False, 'message': 'API not available'}

                async def get_service_pricing(self, *args, **kwargs):
                    """Mock implementation - returns failure response"""
                    _ = args, kwargs  # Acknowledge unused parameters
                    return {'success': False, 'message': 'API not available'}

                async def get_available_services_for_purchase(self, *args, **kwargs):
                    """Mock implementation - returns failure response"""
                    _ = args, kwargs  # Acknowledge unused parameters
                    return {'success': False, 'message': 'API not available'}

                async def purchase_specific_service(self, *args, **kwargs):
                    """Mock implementation - returns failure response"""
                    _ = args, kwargs  # Acknowledge unused parameters
                    return {'success': False, 'message': 'API not available'}

                async def purchase_sms_number(self, *args, **kwargs):
                    """Mock implementation - returns failure response"""
                    _ = args, kwargs  # Acknowledge unused parameters
                    return {'success': False, 'message': 'API not available'}

                async def check_balance(self, *args, **kwargs):
                    """Mock implementation - returns failure response"""
                    _ = args, kwargs  # Acknowledge unused parameters
                    return {'success': False, 'message': 'API not available'}

            # Assign mock classes
            WalletSystem = MockWalletSystem
            SMSPoolAPI = MockSMSPoolAPI

# Load environment variables (override existing ones)
load_dotenv(override=True)

# =============================================================================
# ENHANCED LOGGING CONFIGURATION FOR DEBUGGING
# =============================================================================

# Configure comprehensive logging for debugging
logging.basicConfig(
    level=logging.DEBUG,  # Capture all log levels
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler('logs/ring4_bot.log', encoding='utf-8'),
        logging.StreamHandler()  # Console output
    ]
)

# Create specialized loggers for different components
logger = logging.getLogger(__name__)
api_logger = logging.getLogger('API')
payment_logger = logging.getLogger('PAYMENT')
purchase_logger = logging.getLogger('PURCHASE')
user_logger = logging.getLogger('USER')
performance_logger = logging.getLogger('PERFORMANCE')

# Set log levels for detailed debugging
logging.getLogger('telegram').setLevel(logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)

# =============================================================================
# CONSTANTS & CONFIGURATION (Now using centralized config system)
# =============================================================================

# Initialize configuration manager
config_manager = ConfigurationManager()

# Get configuration values from centralized system
RING4_SERVICE_ID = config_manager.get('RING4_SERVICE_ID')
RING4_COUNTRY_ID = config_manager.get('DEFAULT_COUNTRY_ID')

# SMSPool API Configuration
SMSPOOL_BASE_URL = "https://api.smspool.net"
SMSPOOL_API_KEY = config_manager.get('SMSPOOL_API_KEY')
BOT_TOKEN = config_manager.get('BOT_TOKEN')

# Admin Configuration
ADMIN_IDS = config_manager.get_admin_ids()

# Optimized Polling Configuration (from centralized config)
POLL_INTERVAL = config_manager.get('POLL_INTERVAL')
POLL_TIMEOUT = config_manager.get('POLL_TIMEOUT')
ORDER_EXPIRES_IN = config_manager.get('ORDER_EXPIRES_IN')

# Adaptive polling intervals from config
POLLING_INTERVALS = config_manager.get_polling_intervals()

# Performance optimization constants
MAX_CONSECUTIVE_FAILURES = config_manager.get('MAX_CONSECUTIVE_FAILURES')
API_TIMEOUT_SECONDS = config_manager.get('API_TIMEOUT_SECONDS')
MAX_POLLING_INTERVAL = config_manager.get('MAX_POLLING_INTERVAL')

# Paths (configurable)
DATA_DIR = Path("data")
LOGS_DIR = Path("logs")
# Extract filename
DB_PATH = DATA_DIR / config_manager.get('DATABASE_PATH').split('/')[-1]

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Business configuration
BINANCE_WALLET = config_manager.get('BINANCE_WALLET')

# Check if bot is in maintenance mode
if config_manager.is_maintenance_mode():
    logger.warning("🚧 Bot is in maintenance mode")
    MAINTENANCE_MESSAGE = config_manager.get_maintenance_message()
else:
    MAINTENANCE_MESSAGE = None

logger.info("✅ Configuration loaded from centralized system")
logger.info("📊 Services enabled: %d", len(
    config_manager.get_enabled_services()))
logger.info("👥 Admins configured: %d", len(config_manager.get_admin_ids()))

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================


def setup_logging():
    """Setup production-grade logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler(LOGS_DIR / 'ring4_bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Reduce noise from external libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


logger = setup_logging()

# =============================================================================
# DATABASE OPERATIONS
# =============================================================================


class Database:
    """TinyDB database manager for Ring4 bot"""

    def __init__(self):
        self.db = TinyDB(DB_PATH)
        self.orders = self.db.table('orders')
        self.refunds = self.db.table('refunds')
        logger.info("📄 Database initialized: %s", DB_PATH)

    def create_order(self, user_id: int, order_data: Dict) -> int:
        """Create a new order record"""
        order = {
            'user_id': user_id,
            'order_id': order_data.get('order_id'),
            'number': order_data.get('number'),
            'cost': order_data.get('cost'),
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(seconds=ORDER_EXPIRES_IN)).isoformat(),
            'otp': None,
            'otp_received_at': None
        }
        doc_id = self.orders.insert(order)
        logger.info("📝 Order created: %s for user %s",
                    order['order_id'], user_id)
        return doc_id

    def update_order_status(self, order_id: Union[int, str], status: str, otp: Optional[str] = None):
        """Update order status and OTP if provided"""
        Order = Query()
        update_data = {'status': status}
        if otp:
            update_data['otp'] = otp
            update_data['otp_received_at'] = datetime.now().isoformat()

        self.orders.update(update_data, Order.order_id == order_id)
        logger.info("🔄 Order %s status updated to: %s", order_id, status)

    def get_order(self, order_id: Union[int, str]) -> Optional[Dict]:
        """Get order by ID"""
        Order = Query()
        result = self.orders.search(Order.order_id == order_id)
        return result[0] if result else None

    def get_user_orders(self, user_id: int, status: Optional[str] = None) -> List[Dict]:
        """Get orders for a user, optionally filtered by status"""
        Order = Query()
        if status:
            return [dict(doc) for doc in self.orders.search((Order.user_id == user_id) & (Order.status == status))]
        return [dict(doc) for doc in self.orders.search(Order.user_id == user_id)]

    def create_refund_request(self, user_id: int, order_id: Union[int, str]) -> int:
        """Create a refund request"""
        refund = {
            'user_id': user_id,
            'order_id': order_id,
            'status': 'pending',
            'requested_at': datetime.now().isoformat(),
            'processed_at': None,
            'processed_by': None
        }
        doc_id = self.refunds.insert(refund)
        logger.info("💰 Refund request created for order %s", order_id)
        return doc_id

    def get_pending_refunds(self) -> List[Dict]:
        """Get all pending refund requests"""
        Refund = Query()
        return [dict(doc) for doc in self.refunds.search(Refund.status == 'pending')]

    def update_refund_status(self, order_id: Union[int, str], status: str, admin_id: Optional[int] = None):
        """Update refund request status"""
        Refund = Query()
        update_data = {
            'status': status,
            'processed_at': datetime.now().isoformat()
        }
        if admin_id:
            update_data['processed_by'] = str(admin_id)

        self.refunds.update(update_data, Refund.order_id == order_id)
        logger.info("💰 Refund for order %s status updated to: %s",
                    order_id, status)

    def close(self):
        """Safely close database connections"""
        try:
            if hasattr(self, 'db') and self.db:
                self.db.close()
                logger.debug("🗄️ Database connection closed")
        except OSError as e:
            logger.error("❌ Error closing database: %s", e)


# Global database instance
db = Database()

# Initialize wallet system
wallet_system = None
if WALLET_SYSTEM_AVAILABLE:
    try:
        wallet_system = WalletSystem(db)
        logger.info("✅ Wallet system initialized successfully")
    except (ImportError, AttributeError, RuntimeError) as e:
        logger.error("❌ Failed to initialize wallet system: %s", str(e))
        wallet_system = None

# Ensure we have a wallet system (fallback to mock if needed)
if not wallet_system:
    logger.warning("⚠️ Using mock wallet system - limited functionality")
    wallet_system = WalletSystem(db) if WalletSystem else None

# Configuration constants
BINANCE_WALLET = os.getenv('BINANCE_WALLET', '')
logger.info("✅ Wallet-based system initialized")

# =============================================================================
# SMSPOOL API INTEGRATION
# =============================================================================

# Global API client - Initialize with enhanced error handling
sms_api = None
try:
    if SMSPOOL_API_KEY and SMSPOOL_API_KEY.strip():
        sms_api = SMSPoolAPI(SMSPOOL_API_KEY)
        logger.info("✅ SMSPool API client initialized successfully")
    else:
        logger.error("❌ SMSPOOL_API_KEY is missing or empty")
        logger.warning("⚠️ Running with limited API functionality")
except (ImportError, AttributeError, RuntimeError) as e:
    logger.error("❌ Failed to initialize SMSPool API: %s", str(e))
    logger.warning("⚠️ Bot will continue with limited functionality")

# Ensure sms_api is available even if initialization failed
if sms_api is None and WALLET_SYSTEM_AVAILABLE:
    logger.warning("⚠️ Creating fallback SMSPool API instance")
    try:
        sms_api = SMSPoolAPI(SMSPOOL_API_KEY or "fallback_key")
    except (ImportError, AttributeError, RuntimeError) as fallback_error:
        logger.error("❌ Fallback API creation failed: %s", fallback_error)
        sms_api = None

# =============================================================================
# OTP POLLING SYSTEM
# =============================================================================

# Store active polling tasks
active_polls: Dict[Union[int, str], asyncio.Task] = {}


async def poll_for_otp(order_id: Union[int, str], user_id: int, context: ContextTypes.DEFAULT_TYPE):
