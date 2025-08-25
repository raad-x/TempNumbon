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
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    MenuButton, MenuButtonCommands, MenuButtonWebApp, WebAppInfo,
    BotCommand, BotCommandScopeDefault
)
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
            print("📝 Running in limited mode - wallet functionality disabled")

            # Create minimal fallback classes to prevent AttributeError
            class MockWalletSystem:
                def __init__(self, database):
                    self.db = database
                    self.MIN_DEPOSIT_USD = 1.00
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

                def reserve_balance(self, user_id, amount, order_id, description):
                    """Mock implementation - always returns False"""
                    _ = user_id, amount, order_id, description  # Acknowledge unused parameters
                    return False

                def confirm_reservation(self, user_id, amount, order_id, description):
                    """Mock implementation - always returns False"""
                    _ = user_id, amount, order_id, description  # Acknowledge unused parameters
                    return False

                def cancel_reservation(self, user_id, amount, order_id, reason):
                    """Mock implementation - always returns False"""
                    _ = user_id, amount, order_id, reason  # Acknowledge unused parameters
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

                def create_binance_deposit_request(self, user_id, amount, binance_id):
                    """Mock implementation - returns Binance deposit request structure"""
                    return {
                        'deposit_id': f'BIN_{user_id}_{int(datetime.now().timestamp())}',
                        'amount': amount,
                        'instructions': [
                            "*🟡 Binance Internal Transfer Request*",
                            f"*Amount:* ${amount:.2f}",
                            f"*Binance ID:* `{binance_id}`",
                            "",
                            "📋 *Instructions:*",
                            "1. Open Binance app",
                            "2. Go to Pay > Transfer > To Binance User",
                            f"3. Enter Binance ID: {binance_id}",
                            f"4. Send exactly ${amount:.2f}",
                            f"5. Include your user ID: {user_id} in the note",
                            "",
                            "⚠️ *IMPORTANT:* Internal transfers are instant and free!"
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

                def get_countries_list(self):
                    """Mock implementation - returns empty list"""
                    return []

                def search_countries(self, search_term):
                    """Mock implementation - returns empty list"""
                    _ = search_term  # Acknowledge unused parameter
                    return []

                def get_country_by_id(self, country_id):
                    """Mock implementation - returns None"""
                    _ = country_id  # Acknowledge unused parameter
                    return None

                async def _check_service_purchase_availability(self, *args, **kwargs):
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
BINANCE_ID = config_manager.get('BINANCE_ID')

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
            'otp_received_at': None,
            # Add service and country information for instant refund & reorder
            'service_id': order_data.get('service_id'),
            'service_name': order_data.get('service_name', 'Unknown Service'),
            'country_id': order_data.get('country_id', 1),  # Default to US
            'country_name': order_data.get('country_name', 'United States'),
            'country_flag': order_data.get('country_flag', '🇺🇸'),
            'actual_cost': order_data.get('actual_cost', order_data.get('cost'))
        }
        doc_id = self.orders.insert(order)
        logger.info("📝 Order created: %s for user %s (Service: %s, Country: %s)",
                    order['order_id'], user_id, order.get('service_name'), order.get('country_name'))
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


# Global database instance - Enhanced with Protection
try:
    # Import the new protected database
    from src.protected_database import ProtectedDatabase

    # Initialize with protection enabled
    db = ProtectedDatabase(database_path=str(DB_PATH), enable_protection=True)
    logger.info(
        "✅ Protected Database system initialized with automated 3-day backups")

except ImportError as e:
    logger.warning(f"⚠️ Protected Database not available: {e}")
    logger.info("🔄 Falling back to standard Database")

    # Fallback to standard database
    db = Database()
    logger.info("📄 Standard Database initialized (protection disabled)")

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
    """Optimized high-frequency OTP polling with intelligent intervals"""
    start_time = datetime.now()
    poll_count = 0
    consecutive_failures = 0
    last_status = None

    try:
        user_logger.info(
            "🔄 Starting optimized OTP polling for order %s (user: %s)", order_id, user_id)
        performance_logger.info(
            "⏱️ OTP polling initiated with adaptive intervals")

        if not sms_api:
            logger.error("❌ SMS API not initialized for polling")
            return

        while (datetime.now() - start_time).total_seconds() < POLL_TIMEOUT:
            poll_count += 1
            poll_start = asyncio.get_event_loop().time()

            # Dynamic polling interval based on time elapsed
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed < 60:  # First minute: every 2 seconds
                interval = 2
            elif elapsed < 180:  # Next 2 minutes: every 3 seconds
                interval = 3
            elif elapsed < 300:  # Next 2 minutes: every 5 seconds
                interval = 5
            else:  # After 5 minutes: every 10 seconds
                interval = 10

            api_logger.debug(
                "🔍 Poll #%s for order %s (interval: %ss)", poll_count, order_id, interval)

            try:
                # Check OTP status with timeout
                result = await asyncio.wait_for(
                    sms_api.get_order_status(str(order_id)),
                    timeout=10.0  # 10 second timeout per API call
                )

                poll_duration = asyncio.get_event_loop().time() - poll_start
                performance_logger.debug(
                    "⚡ API status check completed in %.2fs", poll_duration)

                consecutive_failures = 0  # Reset failure counter on success

                if result.get('success'):
                    status = result.get('status', '')

                    # Log status changes for debugging
                    if status != last_status:
                        api_logger.info(
                            "📊 Order %s status changed: %s → %s", order_id, last_status, status)
                        last_status = status

                        # Special logging for processing status (previously thought to be cancelled)
                        if status == 'processing':
                            api_logger.info(
                                "🔄 Order %s is now processing - SMS dispatched, waiting for delivery", order_id)
                        elif status.startswith('unknown_'):
                            api_logger.warning(
                                "⚠️ Order %s has unknown status: %s - continuing to poll", order_id, status)

                    # DEBUG: Log full API response for processing and success status
                    if status in ['processing', 'success']:
                        api_logger.info(
                            "🔍 Order %s API response: status=%s, sms=%s, full_response=%s",
                            order_id, status, result.get('sms'), result)

                    # SUCCESS: OTP received! (Check both 'success' and 'processing' status)
                    # SMSPool API may return SMS content with status 3 (processing)
                    if status in ['success', 'processing'] and (result.get('sms') or result.get('otp')):
                        otp_text = result.get(
                            'sms', '') or result.get('otp', '')

                        # Enhanced OTP extraction with multiple patterns
                        otp_patterns = [
                            r'\b(\d{6})\b',  # 6-digit codes (most common)
                            r'\b(\d{4})\b',  # 4-digit codes
                            r'\b(\d{5})\b',  # 5-digit codes
                            r'\b(\d{7,8})\b',  # 7-8 digit codes
                            # Pattern with keywords
                            r'(?:code|verification|pin):\s*(\d+)',
                            r'(\d+)',  # Any sequence of digits as fallback
                        ]

                        otp_code = None
                        for pattern in otp_patterns:
                            match = re.search(pattern, otp_text, re.IGNORECASE)
                            if match:
                                otp_code = match.group(1)
                                break

                        otp_code = otp_code or otp_text  # Fallback to full text

                        # Update database with detailed info
                        try:
                            # Update order status with OTP completion
                            db.update_order_status(
                                order_id, 'completed', otp_code)

                            # ✅ CRITICAL FIX: Only NOW charge the wallet when OTP is received!
                            order = db.get_order(order_id)
                            if order and wallet_system:
                                reservation_order_id = order.get(
                                    'reservation_order_id')
                                service_cost = order.get('cost', 0)
                                service_name = order.get(
                                    'service_name', 'SMS Service')

                                if reservation_order_id:
                                    # Confirm the reservation by actually deducting from wallet
                                    charge_success = wallet_system.confirm_reservation(
                                        user_id=user_id,
                                        amount=service_cost,
                                        order_id=str(order_id),
                                        description=f"{service_name} service - OTP received"
                                    )

                                    if charge_success:
                                        purchase_logger.info(
                                            "💰 WALLET CHARGED: User %s charged $%.2f for order %s (OTP received)",
                                            user_id, service_cost, order_id)
                                    else:
                                        logger.error(
                                            "❌ CRITICAL: Failed to charge user %s for completed order %s",
                                            user_id, order_id)
                                else:
                                    logger.warning(
                                        "⚠️ No reservation_order_id found for order %s - cannot charge wallet",
                                        order_id)

                            user_logger.info(
                                "✅ Order %s completed - OTP: %s - WALLET CHARGED", order_id, otp_code)
                        except (OSError, RuntimeError, ValueError) as db_err:
                            logger.error(
                                "❌ Database update failed: %s", db_err)

                        # Send optimized success message to user
                        # Create buttons for after OTP is received
                        success_keyboard = []

                        # Get order details for Order Again button
                        order = db.get_order(order_id)

                        # Add Order Again button if we have service details
                        if order and order.get('service_id') and order.get('country_id'):
                            service_name = order.get(
                                'service_name', 'Same Service')
                            country_flag = order.get('country_flag', '🌍')
                            success_keyboard.append([
                                InlineKeyboardButton(
                                    f"� Order Again ({service_name} in {country_flag})",
                                    callback_data=f"order_again_{order_id}"
                                )
                            ])

                        success_keyboard.extend([
                            [
                                InlineKeyboardButton(
                                    "📱 Browse Services", callback_data="browse_services"),
                                InlineKeyboardButton(
                                    "💰 Check Wallet", callback_data="show_balance")
                            ],
                            [
                                InlineKeyboardButton(
                                    "🆔 Order History", callback_data="transaction_history"),
                                InlineKeyboardButton(
                                    "🏠 Main Menu", callback_data="back_to_start")
                            ]
                        ])
                        success_reply_markup = InlineKeyboardMarkup(
                            success_keyboard)

                        total_time = (datetime.now() -
                                      start_time).total_seconds()
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"🎉 <b>OTP Code Received!</b>\n\n"
                            f"👉 <b>Your Code:</b> <code>{otp_code}</code>\n\n"
                            f"📱 <b>Full SMS:</b> {otp_text}\n\n"
                            f"🆔 <b>Order:</b> #{order_id}\n"
                            f"⚡ <b>Delivery Time:</b> {total_time:.1f} seconds\n"
                            f"🔄 <b>Polls Required:</b> {poll_count}\n\n"
                            f"✨ <b>Ready to use immediately!</b>",
                            parse_mode='HTML',
                            reply_markup=success_reply_markup
                        )

                        performance_logger.info(
                            "🎯 OTP delivered for order %s in %.1fs after %s polls", order_id, total_time, poll_count)
                        break

                    # Handle terminal status states (should stop polling)
                    elif status in ['cancelled', 'expired', 'timeout']:
                        api_logger.warning(
                            "🛑 Order %s reached terminal status: %s - stopping polling", order_id, status)

                        # Update database status
                        try:
                            db.update_order_status(order_id, status)
                        except (OSError, RuntimeError, ValueError) as db_err:
                            logger.error(
                                "❌ Database status update failed: %s", db_err)

                        # Notify user about terminal status
                        terminal_keyboard = []

                        terminal_keyboard.extend([
                            [
                                InlineKeyboardButton(
                                    "↩️ Request Return", callback_data=f"refund_{order_id}"),
                                InlineKeyboardButton(
                                    "🔄 Try Again", callback_data="browse_services")
                            ],
                            [
                                InlineKeyboardButton(
                                    "💰 Check Wallet", callback_data="show_balance"),
                                InlineKeyboardButton(
                                    "🏠 Main Menu", callback_data="back_to_start")
                            ]
                        ])

                        # Add Order Again button at the bottom if we have service details
                        order = db.get_order(order_id)
                        if order and order.get('service_id') and order.get('country_id'):
                            service_name = order.get(
                                'service_name', 'Same Service')
                            country_flag = order.get('country_flag', '🌍')
                            terminal_keyboard.append([
                                InlineKeyboardButton(
                                    f"🔄 Order Again ({service_name} in {country_flag})",
                                    callback_data=f"order_again_{order_id}"
                                )
                            ])

                        terminal_reply_markup = InlineKeyboardMarkup(
                            terminal_keyboard)

                        status_messages = {
                            'cancelled': '🚫 <b>Order Cancelled</b>\n\nThis order was cancelled by the provider.',
                            'expired': '⏰ <b>Order Expired</b>\n\nThis order has expired and is no longer active.',
                            'timeout': '🕒 <b>Order Timeout</b>\n\nThis order timed out waiting for SMS delivery.'
                        }

                        total_time = (datetime.now() -
                                      start_time).total_seconds()
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"{status_messages.get(status, '❌ Order Failed')}\n\n"
                            f"🆔 <b>Order:</b> #{order_id}\n"
                            f"⏱️ <b>Duration:</b> {total_time:.1f} seconds\n"
                            f"🔄 <b>Total Polls:</b> {poll_count}\n\n"
                            f"↩️ <b>Return available</b> - Use button below to request return.",
                            parse_mode='HTML',
                            reply_markup=terminal_reply_markup
                        )
                        break

                    # Continue polling for pending/processing statuses
                    # (no action needed - loop will continue)

            except asyncio.TimeoutError:
                consecutive_failures += 1
                api_logger.warning(
                    "⏰ Timeout during poll #%s for order %s (attempt %s)",
                    poll_count, order_id, consecutive_failures)

                # Stop if too many consecutive timeouts
                if consecutive_failures >= 3:
                    api_logger.error(
                        "❌ Too many consecutive timeouts for order %s - stopping polling", order_id)
                    break

            except Exception as api_error:
                consecutive_failures += 1
                api_logger.error(
                    "❌ API error during poll #%s for order %s: %s", poll_count, order_id, str(api_error))

                # Stop if too many consecutive failures
                if consecutive_failures >= 5:
                    api_logger.error(
                        "❌ Too many consecutive failures for order %s - stopping polling", order_id)
                    break

            # Adaptive sleep based on current interval
            await asyncio.sleep(interval)

        else:
            # TIMEOUT: No OTP received within time limit - CANCEL RESERVATION (no refund needed)
            try:
                # Get order details before processing cancellation
                order = db.get_order(order_id)
                if order:
                    # Cancel reservation since no OTP was received (no actual charge occurred)
                    if wallet_system:
                        reservation_order_id = order.get(
                            'reservation_order_id')
                        service_cost = order.get('cost', 0)

                        if reservation_order_id:
                            cancel_success = wallet_system.cancel_reservation(
                                user_id=user_id,
                                amount=service_cost,
                                order_id=str(order_id),
                                reason="SMS timeout - no OTP received"
                            )

                            if cancel_success:
                                # Update order status to timeout (not refunded since no charge occurred)
                                db.update_order_status(order_id, 'timeout')
                                purchase_logger.info(
                                    "⏰ RESERVATION CANCELLED: User %s order %s timed out - no charge occurred",
                                    user_id, order_id)
                                # Cancel order with SMS Bot if available
                                if sms_api:
                                    try:
                                        cancel_result = await sms_api.cancel_order(str(order_id))
                                        if cancel_result.get('success'):
                                            logger.info(
                                                "✅ Timeout order %s cancelled with SMS Bot", order_id)
                                        else:
                                            logger.warning(
                                                "⚠️ Failed to cancel timeout order %s with SMS Bot", order_id)
                                    except Exception as cancel_error:
                                        logger.error(
                                            "❌ Error cancelling timeout order %s: %s", order_id, cancel_error)
                            else:
                                # Fallback to timeout status if cancellation fails
                                db.update_order_status(order_id, 'timeout')
                        else:
                            # No reservation found, just mark as timeout
                            db.update_order_status(order_id, 'timeout')
                    else:
                        # No wallet system, just mark as timeout
                        db.update_order_status(order_id, 'timeout')
                else:
                    logger.error(
                        "❌ Order %s not found for timeout processing", order_id)

            except (OSError, RuntimeError, ValueError) as db_err:
                logger.error("❌ Database timeout update failed: %s", db_err)
                # Fallback to timeout status
                try:
                    db.update_order_status(order_id, 'timeout')
                except Exception:
                    pass

            # Get order details for Order Again button
            order = db.get_order(order_id)

            # Create keyboard with Order Again button for timeout scenario
            timeout_keyboard = []

            timeout_keyboard.extend([
                [
                    InlineKeyboardButton(
                        "🔍 Explore Services", callback_data="browse_services"),
                    InlineKeyboardButton(
                        "� Check Balance", callback_data="show_balance")
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_to_start")
                ]
            ])

            # Add Order Again button at the bottom if we have service details
            if order and order.get('service_id') and order.get('country_id'):
                service_name = order.get('service_name', 'Same Service')
                country_flag = order.get('country_flag', '🌍')
                timeout_keyboard.append([
                    InlineKeyboardButton(
                        f"🔄 Order Again ({service_name} in {country_flag})",
                        callback_data=f"order_again_{order_id}"
                    )
                ])
            timeout_reply_markup = InlineKeyboardMarkup(timeout_keyboard)

            total_time = (datetime.now() - start_time).total_seconds()
            # Get current balance (no refund needed since no charge occurred)
            user_balance = wallet_system.get_user_balance(
                user_id) if wallet_system else 0

            await context.bot.send_message(
                chat_id=user_id,
                text=f"⏰ <b>SMS Delivery Timeout</b>\n\n"
                f"🆔 <b>Order:</b> #{order_id}\n"
                f"⏱️ <b>Duration:</b> {POLL_TIMEOUT//60} minutes\n"
                f"🔄 <b>Total Polls:</b> {poll_count}\n\n"
                f"💰 <b>Good News:</b> No charge to your wallet!\n"
                f"💰 <b>Current Balance:</b> ${user_balance:.2f}\n\n"
                f"You can try ordering again anytime or use 'Order Again' for the same service!",
                parse_mode='HTML',
                reply_markup=timeout_reply_markup
            )

            performance_logger.warning(
                "⏰ Order %s timed out after %s polls in %.1fs", order_id, poll_count, total_time)

    except asyncio.CancelledError:
        user_logger.info(
            "🛑 OTP polling cancelled for order %s after %s polls", order_id, poll_count)
        raise
    except Exception as e:
        logger.error(
            "❌ Critical error in OTP polling for order %s: %s", order_id, str(e))

        # Get order details and automatically cancel reservation for error
        try:
            order = db.get_order(order_id)
            if order:
                # Cancel reservation since error occurred (no actual charge occurred)
                if wallet_system:
                    reservation_order_id = order.get('reservation_order_id')
                    service_cost = order.get('cost', 0)

                    if reservation_order_id:
                        cancel_success = wallet_system.cancel_reservation(
                            user_id=user_id,
                            amount=service_cost,
                            order_id=str(order_id),
                            reason="Service error - cancelling reservation"
                        )

                        if cancel_success:
                            # Update order status to error (not refunded since no charge occurred)
                            db.update_order_status(order_id, 'error')
                            purchase_logger.info(
                                "❌ RESERVATION CANCELLED: User %s order %s had error - no charge occurred",
                                user_id, order_id)
                            # Cancel order with SMS Bot if available
                            if sms_api:
                                try:
                                    cancel_result = await sms_api.cancel_order(str(order_id))
                                    if cancel_result.get('success'):
                                        logger.info(
                                            "✅ Error order %s cancelled with SMS Bot", order_id)
                                except Exception as cancel_error:
                                    logger.error(
                                        "❌ Error cancelling error order %s: %s", order_id, cancel_error)
                        else:
                            # Fallback to error status if cancellation fails
                            db.update_order_status(order_id, 'error')
                    else:
                        # No reservation found, just mark as error
                        db.update_order_status(order_id, 'error')
                else:
                    # No wallet system, just mark as error
                    db.update_order_status(order_id, 'error')
            else:
                # Safely update database status if possible
                db.update_order_status(order_id, 'error')
        except Exception as db_error:
            logger.error(
                "❌ Failed to update order status during error handling: %s", db_error)

        # Send error notification to user
        try:
            error_keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 Try Again", callback_data="browse_services"),
                    InlineKeyboardButton(
                        "💰 Check Balance", callback_data="show_balance")
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_to_start")
                ]
            ]
            error_reply_markup = InlineKeyboardMarkup(error_keyboard)

            # Get current balance (no refund needed since no charge occurred)
            user_balance = wallet_system.get_user_balance(
                user_id) if wallet_system else 0

            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ <b>Service Error</b>\n\n"
                f"🆔 <b>Order:</b> #{order_id}\n"
                f"🔄 <b>Polls:</b> {poll_count}\n\n"
                f"💰 <b>Good News:</b> No charge to your wallet!\n"
                f"💰 <b>Current Balance:</b> ${user_balance:.2f}\n\n"
                f"You can try ordering again anytime.",
                parse_mode='HTML',
                reply_markup=error_reply_markup
            )
        except Exception as notification_error:
            logger.error(
                "❌ Failed to send error notification: %s", notification_error)

    finally:
        performance_logger.info(
            "🧹 Polling cleanup completed for order %s", order_id)

        # Remove from active polls tracking
        if order_id in active_polls:
            active_polls.pop(order_id, None)


def start_otp_polling(order_id: Union[int, str], user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Start OTP polling task"""
    if order_id in active_polls:
        active_polls[order_id].cancel()

    task = asyncio.create_task(poll_for_otp(order_id, user_id, context))
    active_polls[order_id] = task
    return task

# =============================================================================
# PERSISTENT MENU SYSTEM
# =============================================================================


async def setup_bot_menu(application: Application):
    """Setup persistent bot menu and commands"""
    try:
        # Define comprehensive bot commands for the menu
        commands = [
            BotCommand("start", "🏠 Main interface & dashboard"),
            BotCommand("buy", "📱 Get US phone number instantly"),
            BotCommand("services", "🔍 Browse all available services"),
            BotCommand("deposit", "💰 Add wallet credit"),
            BotCommand("balance", "� Check wallet & transactions"),
            BotCommand("orders", "📋 View order history"),
            BotCommand("refund", "↩️ Process instant returns"),
            BotCommand("help", "💬 Support & instructions"),
            BotCommand("contact", "📞 Contact customer support"),
            BotCommand("admin", "👨‍💼 Admin panel (admin only)"),
            BotCommand("status", "🔧 Service status (admin only)"),
        ]

        # Set bot commands (this creates the persistent menu)
        await application.bot.set_my_commands(
            commands=commands,
            scope=BotCommandScopeDefault()
        )

        # Set menu button to show commands
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonCommands()
        )

        logger.info("✅ Enhanced persistent menu system configured successfully")
        logger.info("📋 Commands available in menu: %d", len(commands))

    except Exception as e:
        logger.error("❌ Failed to setup bot menu: %s", str(e))


async def setup_user_specific_menu(bot, user_id: int, is_admin: bool = False):
    """Setup user-specific menu based on permissions"""
    try:
        # Base commands for all users
        commands = [
            BotCommand("start", "🏠 Main interface & dashboard"),
            BotCommand("buy", "📱 Get US phone number instantly"),
            BotCommand("services", "🔍 Browse all available services"),
            BotCommand("deposit", "💰 Add wallet credit"),
            BotCommand("balance", "� Check wallet & transactions"),
            BotCommand("orders", "📋 View order history"),
            BotCommand("refund", "↩️ Process instant returns"),
            BotCommand("help", "💬 Support & instructions"),
            BotCommand("contact", "📞 Contact customer support"),
        ]

        # Add admin commands for admins
        if is_admin:
            commands.extend([
                BotCommand("admin", "👨‍💼 Admin panel"),
                BotCommand("status", "🔧 Check service status"),
            ])

        # Set user-specific commands (if needed in future)
        # For now, we use the same commands for everyone
        logger.debug("📋 Enhanced menu setup for user %s (%s commands)",
                     user_id, len(commands))

    except Exception as e:
        logger.error("❌ Failed to setup user menu for %s: %s", user_id, str(e))


def get_quick_action_keyboard(user_balance: float = 0.00, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Generate enhanced quick action keyboard based on user state"""
    keyboard = []

    # Row 1: Primary actions based on balance
    if user_balance >= 0.15:
        keyboard.append([
            InlineKeyboardButton(
                "📱 Get Number", callback_data="browse_services"),
            InlineKeyboardButton("💰 Wallet", callback_data="show_balance")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                "💵 Add Credit", callback_data="deposit_funds"),
            InlineKeyboardButton("🔍 Explore", callback_data="browse_services")
        ])

    # Row 2: Order management actions
    keyboard.append([
        InlineKeyboardButton("📋 Orders", callback_data="my_orders"),
        InlineKeyboardButton("↩️ Returns", callback_data="quick_refund")
    ])

    # Row 3: Service and transaction actions
    keyboard.append([
        InlineKeyboardButton("🔍 Services", callback_data="browse_services"),
        InlineKeyboardButton("📊 History", callback_data="transaction_history")
    ])

    # Row 4: Support and utility actions
    keyboard.append([
        InlineKeyboardButton("💬 Support", callback_data="show_help"),
        InlineKeyboardButton("� Contact", callback_data="contact_us")
    ])

    # Row 5: Refresh and admin actions
    keyboard.append([
        InlineKeyboardButton("�🔄 Refresh", callback_data="start_menu")
    ])

    # Row 6: Admin actions (if admin)
    if is_admin:
        keyboard.append([
            InlineKeyboardButton(
                "👨‍💼 Admin Panel", callback_data="admin_panel"),
            InlineKeyboardButton("🔧 Services", callback_data="service_status")
        ])

    return InlineKeyboardMarkup(keyboard)


async def handle_my_orders(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle my orders callback"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    # Get user orders
    orders = db.get_user_orders(user.id)

    if not orders:
        await query.edit_message_text(
            "📋 <b>Your Orders</b>\n\n"
            "❌ No orders found.\n\n"
            "💡 Use /buy to get your first US phone number!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "📱 Get Number", callback_data="browse_services"),
                InlineKeyboardButton("🔙 Back", callback_data="start_menu")
            ]])
        )
        return

    # Sort orders by creation date (newest first)
    orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # Limit to last 10 orders for better UX
    recent_orders = orders[:10]

    orders_text = "📋 <b>Recent Orders</b>\n\n"

    for i, order in enumerate(recent_orders, 1):
        status_emoji = {
            'pending': '🟡',
            'processing': '🔄',
            'completed': '✅',
            'timeout': '⏰',
            'refunded': '💰',
            'cancelled': '🚫',
            'error': '❌'
        }

        emoji = status_emoji.get(order['status'], '❔')
        created = datetime.fromisoformat(
            order['created_at']).strftime('%m/%d %H:%M')

        orders_text += (
            f"{emoji} <b>#{order['order_id']}</b>\n"
            f"📱 <code>{order['number']}</code>\n"
            f"💰 ${order['cost']} • {created}\n"
        )

        if order.get('otp'):
            orders_text += f"🔐 Code: <code>{order['otp']}</code>\n"

        orders_text += f"Status: {order['status'].title()}\n\n"

    if len(orders) > 10:
        orders_text += f"... and {len(orders) - 10} more orders\n\n"

    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 Quick Return", callback_data="quick_refund"),
            InlineKeyboardButton("📱 Get More", callback_data="browse_services")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="start_menu")
        ]
    ]

    await query.edit_message_text(
        orders_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_quick_refund(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle quick refund - shows refundable orders immediately"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    # Get refundable orders - EXCLUDE already refunded orders to prevent duplicate refunds
    orders = db.get_user_orders(user.id)
    refundable = [o for o in orders if o['status'] in [
        'pending', 'timeout', 'error', 'cancelled'] and o['status'] != 'refunded']

    if not refundable:
        await query.edit_message_text(
            "↩️ <b>Quick Returns</b>\n\n"
            "❌ No returnable orders found.\n\n"
            "💡 Only pending, timeout, error, or cancelled orders can be returned.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "📋 View Orders", callback_data="my_orders"),
                InlineKeyboardButton("🔙 Back", callback_data="start_menu")
            ]])
        )
        return

    keyboard = []
    for order in refundable:
        created = datetime.fromisoformat(
            order['created_at']).strftime('%m/%d %H:%M')
        service_name = order.get('service_name', 'Unknown Service')
        country_flag = order.get('country_flag', '🇺🇸')
        country_name = order.get('country_name', 'United States')

        # Regular refund button
        keyboard.append([
            InlineKeyboardButton(
                f"↩️ Return Only: #{order['order_id']} - ${order['cost']} ({service_name}, {country_flag} {country_name[:2]}...)",
                callback_data=f"refund_{order['order_id']}"
            )
        ])

        # Instant refund & get another number button (only if sufficient balance for reorder)
        user_balance = wallet_system.get_user_balance(
            user.id) if wallet_system else 0.00
        order_cost = float(order.get('cost', 0))

        # Check if user has sufficient balance after refund for reorder
        balance_after_refund = user_balance + order_cost
        if balance_after_refund >= order_cost:
            keyboard.append([
                InlineKeyboardButton(
                    f"🔄 Return & Replace: {service_name} ({country_flag})",
                    callback_data=f"refund_reorder_{order['order_id']}"
                )
            ])

    keyboard.append([
        InlineKeyboardButton("🔙 Back", callback_data="start_menu")
    ])

    refund_text = (
        f"↩️ <b>Quick Return Options</b>\n\n"
        f"Choose your return option:\n\n"
        f"↩️ <b>Return Only:</b> Money back to wallet\n"
        f"🔄 <b>Return & Replace:</b> Instant replacement with same service & country\n\n"
        f"📊 Returnable orders: {len(refundable)}\n"
        f"🚀 <b>No confirmation needed!</b>"
    )

    await query.edit_message_text(
        refund_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_show_help(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle help callback"""
    if not update.callback_query:
        return

    query = update.callback_query
    await query.answer()

    help_text = (
        "💡 <b>Complete Quick Start Guide</b>\n\n"
        "<b>🚀 Getting Started (3 Steps)</b>\n"
        "1️⃣ Add credit to wallet (min $5) - /deposit\n"
        "2️⃣ Get phone number (from $0.17) - /buy\n"
        "3️⃣ Use for verification & receive SMS automatically\n\n"
        "<b>🎯 Enhanced Menu Features</b>\n"
        "• 📱 /buy - Get Number instantly\n"
        "• 🔍 /services - Browse all services\n"
        "• 💵 /deposit - Add Credit to wallet\n"
        "• 💰 /balance - Wallet & transactions\n"
        "• 📋 /orders - View order history\n"
        "• ↩️ /refund - Smart refund options\n"
        "• 💬 /help - This comprehensive guide\n"
        "• 🔄 Refresh - Update interface\n\n"
        "<b>🔄 Smart Returns (Enhanced)</b>\n"
        "• ↩️ <b>Return Only:</b> Money back to wallet\n"
        "• 🔄 <b>Return & Replace:</b> Instant new number\n"
        "  - Same service & country automatically\n"
        "  - No confirmations needed\n"
        "  - Perfect for getting fresh numbers\n\n"
        "<b>💡 Pro Tips & Features</b>\n"
        "• All returns are automatic\n"
        "• Numbers expire in 10 minutes\n"
        "• Use the enhanced menu bar for fastest access\n"
        "• Multiple services as backup\n"
        "• Smart reorder saves preferences\n"
        "• Complete order tracking\n"
        "• Transaction history available\n"
        "• Enhanced UX with comprehensive menu\n\n"
        "<b>🔍 Service Options</b>\n"
        "• Browse all available services via /services\n"
        "• Multiple countries supported\n"
        "• Real-time availability checking\n"
        "• Transparent pricing\n\n"
        "<b>🆘 Need Help?</b>\n"
        "Contact an administrator for support.\n"
        "All features now accessible via enhanced menu!"
    )

    keyboard = [
        [
            InlineKeyboardButton("📱 Try Now", callback_data="browse_services"),
            InlineKeyboardButton("💵 Add Credit", callback_data="deposit_funds")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="start_menu")
        ]
    ]

    await query.edit_message_text(
        help_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_contact_us(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle contact us callback"""
    if not update.callback_query:
        return

    query = update.callback_query
    await query.answer()

    # Get contact accounts from configuration
    contact_accounts = config_manager.get_contact_accounts()

    if not contact_accounts:
        contact_text = (
            "📞 <b>Contact Us</b>\n\n"
            "❌ Contact information not configured.\n"
            "Please contact an administrator for assistance."
        )
    else:
        # Build contact text with available accounts
        contact_links = []
        for account in contact_accounts:
            if account:  # Make sure account is not empty
                contact_links.append(f"@{account}")

        if contact_links:
            contact_text = (
                "📞 <b>Contact Us</b>\n\n"
                "For enquiries, please get in touch with us through:\n\n"
                f"{'  •  '.join(contact_links)}\n\n"
                "💬 Feel free to reach out for:\n"
                "• Account support\n"
                "• Deposit assistance\n"
                "• Technical issues\n"
                "• General inquiries\n\n"
                "⚡ We typically respond within a few hours!"
            )
        else:
            contact_text = (
                "📞 <b>Contact Us</b>\n\n"
                "❌ Contact information not available.\n"
                "Please contact an administrator for assistance."
            )

    keyboard = [
        [
            InlineKeyboardButton("💬 Support", callback_data="show_help"),
            InlineKeyboardButton(
                "📱 Get Started", callback_data="browse_services")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="start_menu")
        ]
    ]

    await query.edit_message_text(
        contact_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_admin_panel(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel callback"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    if not is_admin(user.id):
        await query.answer("❌ Admin access required", show_alert=True)
        return

    await query.answer()

    # Get system stats
    all_orders = db.orders.all()
    status_counts = {}
    total_revenue = 0
    today = datetime.now().date()

    for order in all_orders:
        status = order.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

        if status == 'completed':
            total_revenue += float(order.get('cost', 0))

    admin_text = (
        f"👨‍💼 <b>Enhanced Admin Control Panel</b>\n\n"
        f"📊 <b>System Statistics:</b>\n"
        f"• Total Orders: {len(all_orders)}\n"
        f"• ✅ Completed: {status_counts.get('completed', 0)}\n"
        f"• 🟡 Pending: {status_counts.get('pending', 0)}\n"
        f"• ⏰ Timeout: {status_counts.get('timeout', 0)}\n"
        f"• ↩️ Refunded: {status_counts.get('refunded', 0)}\n"
        f"• ❌ Errors: {status_counts.get('error', 0)}\n\n"
        f"💰 <b>Revenue:</b> ${total_revenue:.2f}\n"
        f"🔄 <b>Active Polls:</b> {len(active_polls)}\n\n"
        f"🤖 <b>Bot Status:</b> ✅ Running with Enhanced Menu\n"
        f"🚀 <b>Auto-Refunds:</b> ✅ Enabled\n"
        f"🎯 <b>Menu System:</b> ✅ Enhanced with all features\n\n"
        f"📋 <b>Available Admin Commands:</b>\n"
        f"• /admin - This panel\n"
        f"• /status - Service status check\n"
        f"• Enhanced menu with quick access to all features"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "⚙️ Services", callback_data="service_status"),
            InlineKeyboardButton(
                "💰 Deposits", callback_data="pending_deposits")
        ],
        [
            InlineKeyboardButton(
                "📊 Full Stats", callback_data="detailed_stats"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_panel")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="start_menu")
        ]
    ]

    await query.edit_message_text(
        admin_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_pending_deposits(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle pending deposits admin view"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    if not is_admin(user.id):
        await query.answer("❌ Admin access required", show_alert=True)
        return

    await query.answer()

    if not wallet_system:
        await query.edit_message_text(
            "❌ <b>Wallet System Unavailable</b>\n\n"
            "The wallet system is not properly configured.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
            ]])
        )
        return

    # Get pending deposits from wallet system
    pending_deposits = wallet_system.get_pending_deposits()

    if not pending_deposits:
        pending_text = (
            "💰 <b>Pending Deposits</b>\n\n"
            "No pending deposits at this time.\n\n"
            "💡 Users will see deposit instructions when they request funding."
        )
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔄 Refresh", callback_data="pending_deposits"),
                InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
            ]
        ]
    else:
        pending_text = "💰 <b>Pending Deposits</b>\n\n"
        keyboard = []

        for deposit in pending_deposits:
            deposit_id = deposit['deposit_id']
            user_id = deposit['user_id']
            amount = deposit['amount_usd']
            method = deposit.get('deposit_method', 'wallet')
            created_at = datetime.fromisoformat(
                deposit['created_at']).strftime('%Y-%m-%d %H:%M')

            method_emoji = "🟡" if method == 'binance' else "💳"
            method_text = "Binance" if method == 'binance' else "Wallet"

            pending_text += (
                f"{method_emoji} <b>${amount:.2f}</b> - {method_text}\n"
                f"👤 User: <code>{user_id}</code>\n"
                f"🆔 ID: <code>{deposit_id}</code>\n"
                f"⏰ Created: {created_at}\n\n"
            )

            # Add approve/deny buttons for each deposit
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ Approve ${amount:.2f}",
                    callback_data=f"approve_deposit_{deposit_id}"),
                InlineKeyboardButton(
                    f"❌ Deny ${amount:.2f}",
                    callback_data=f"deny_deposit_{deposit_id}")
            ])

        # Add refresh and back buttons at the end
        keyboard.append([
            InlineKeyboardButton(
                "🔄 Refresh", callback_data="pending_deposits"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
        ])

    await query.edit_message_text(
        pending_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_detailed_stats(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle detailed statistics admin view"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    if not is_admin(user.id):
        await query.answer("❌ Admin access required", show_alert=True)
        return

    await query.answer()

    # Get detailed statistics
    all_orders = db.orders.all()

    # Calculate date-based stats
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    today_orders = []
    yesterday_orders = []
    week_orders = []

    for order in all_orders:
        try:
            order_date = datetime.fromisoformat(order['created_at']).date()
            if order_date == today:
                today_orders.append(order)
            elif order_date == yesterday:
                yesterday_orders.append(order)
            elif order_date >= week_ago:
                week_orders.append(order)
        except (ValueError, KeyError):
            continue

    # Calculate revenue
    today_revenue = sum(float(o.get('cost', 0))
                        for o in today_orders if o.get('status') == 'completed')
    week_revenue = sum(float(o.get('cost', 0))
                       for o in week_orders if o.get('status') == 'completed')
    total_revenue = sum(float(o.get('cost', 0))
                        for o in all_orders if o.get('status') == 'completed')

    stats_text = (
        f"📊 <b>Detailed Statistics</b>\n\n"
        f"📅 <b>Today:</b>\n"
        f"• Orders: {len(today_orders)}\n"
        f"• Revenue: ${today_revenue:.2f}\n\n"
        f"📅 <b>Yesterday:</b>\n"
        f"• Orders: {len(yesterday_orders)}\n\n"
        f"📅 <b>Last 7 Days:</b>\n"
        f"• Orders: {len(week_orders)}\n"
        f"• Revenue: ${week_revenue:.2f}\n\n"
        f"📈 <b>All Time:</b>\n"
        f"• Total Orders: {len(all_orders)}\n"
        f"• Total Revenue: ${total_revenue:.2f}\n"
        f"• Active Polls: {len(active_polls)}\n\n"
        f"🔧 <b>System Health:</b>\n"
        f"• Database: ✅ Connected\n"
        f"• API: {'✅ Active' if sms_api else '❌ Inactive'}\n"
        f"• Wallet: {'✅ Active' if wallet_system else '❌ Inactive'}"
    )

    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="detailed_stats"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
        ]
    ]

    await query.edit_message_text(
        stats_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def clean_html_message(message: str) -> str:
    """Clean HTML tags from error messages and extract meaningful content"""

    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', message)

    # Replace multiple spaces/newlines with single space
    clean_text = re.sub(r'\s+', ' ', clean_text.strip())

    # Extract specific error patterns
    if 'couldn\'t find an available phone number' in clean_text:
        return 'No Ring4 numbers available at the moment'
    elif 'No numbers available at the moment' in clean_text:
        return 'Ring4 service temporarily unavailable'
    elif 'country & service you have selected is not valid' in clean_text:
        return 'Ring4 service configuration issue'
    elif clean_text and len(clean_text) > 200:
        # Truncate very long messages
        return clean_text[:200] + '...'

    return clean_text or 'Unknown service error'


def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in ADMIN_IDS


def format_order_info(order: Dict) -> str:
    """Format order information for display"""
    created = datetime.fromisoformat(
        order['created_at']).strftime('%Y-%m-%d %H:%M')
    status_emoji = {
        'pending': '🟡',
        'processing': '🔄',
        'completed': '✅',
        'timeout': '⏰',
        'refunded': '↩️',
        'cancelled': '🚫',
        'error': '❌'
    }

    # Get service and country info if available
    service_name = order.get('service_name', 'Unknown Service')
    country_name = order.get('country_name', 'Unknown Country')
    country_flag = order.get('country_flag', '🌍')

    base_info = (
        f"{status_emoji.get(order['status'], '❔')} <b>Order #{order['order_id']}</b>\n"
        f"📱 Number: <code>{order['number']}</code>\n"
        f"🏷️ Service: {service_name}\n"
        f"🌍 Country: {country_flag} {country_name}\n"
        f"💰 Price: ${order['cost']}\n"
        f"📅 Created: {created}\n"
        f"📊 Status: {order['status'].title()}"
    )

    return base_info

# =============================================================================
# TELEGRAM COMMAND HANDLERS
# =============================================================================


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with enhanced menu integration"""
    _ = context  # Acknowledge unused parameter
    if not update.effective_user or not update.message:
        return

    user = update.effective_user
    user_balance = wallet_system.get_user_balance(
        user.id) if wallet_system else 0.00

    # Setup user-specific menu (if needed)
    await setup_user_specific_menu(update.get_bot(), user.id, is_admin(user.id))

    # Create enhanced quick action keyboard
    reply_markup = get_quick_action_keyboard(user_balance, is_admin(user.id))

    welcome_text = (
        f"📱 <b>SMS Verification Service</b>\n\n"
        f"💰 <b>Balance:</b> ${user_balance:.2f}\n\n"
        f"🎯 <b>Quick Access</b>\n"
        f"Use buttons below or the menu bar for instant actions\n\n"
        f"✨ <b>Features</b>\n"
        f"• 📱 Instant US phone numbers\n"
        f"• ⚡ Real-time SMS delivery\n"
        f"• 🔄 Smart refund system\n"
        f"• 📦 Complete order tracking\n\n"
        f"💡 <b>Tip:</b> Access all features via the menu button next to chat input"
    )

    if user_balance < 0.15:
        welcome_text += (
            f"\n\n🚀 <b>Get Started</b>\n"
            f"Add credit to your wallet to start getting phone numbers instantly"
        )
    else:
        welcome_text += (
            f"\n\n✅ <b>Ready to Go</b>\n"
            f"You have sufficient balance for phone number purchases"
        )

    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

    username = user.username or "Unknown"
    logger.info(
        "👋 Start command from user %s (@%s) - Balance: $%.2f", user.id, username, user_balance)


async def handle_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start menu callback - shows main menu"""
    if not update.effective_user:
        return

    user = update.effective_user
    user_balance = wallet_system.get_user_balance(
        user.id) if wallet_system else 0.00

    # Create enhanced quick action keyboard
    reply_markup = get_quick_action_keyboard(user_balance, is_admin(user.id))

    welcome_text = (
        f"📱 <b>SMS Verification Service</b>\n\n"
        f"💰 <b>Balance:</b> ${user_balance:.2f}\n\n"
        f"🎯 <b>Enhanced Quick Access</b>\n"
        f"Use buttons below or the comprehensive menu bar for instant actions\n\n"
        f"✨ <b>Premium Features</b>\n"
        f"• 📱 Instant US phone numbers\n"
        f"• ⚡ Real-time SMS delivery\n"
        f"• 🔄 Smart return system with instant replacements\n"
        f"• 📊 Complete order tracking & history\n"
        f"• 💳 Comprehensive wallet management\n"
        f"• 🔍 Browse all available services\n"
        f"• 📋 Enhanced order management\n\n"
        f"🚀 <b>New Menu Features</b>\n"
        f"• /services - Browse all available services\n"
        f"• /orders - Complete order history\n"
        f"• /balance - Enhanced wallet & transactions\n"
        f"• Quick access to all features via menu\n\n"
        f"💡 <b>Pro Tip:</b> Access all features via the enhanced menu button next to chat input"
    )

    if user_balance < 0.15:
        welcome_text += (
            f"\n\n🚀 <b>Get Started</b>\n"
            f"Add credit to your wallet to start getting phone numbers instantly"
        )
    else:
        welcome_text += (
            f"\n\n✅ <b>Ready to Go</b>\n"
            f"You have sufficient balance for phone number purchases"
        )

    # Try to edit the message, fallback to new message if needed
    try:
        query = update.callback_query
        if query:
            await query.edit_message_text(
                welcome_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            await query.answer()
        else:
            if update.message:
                await update.message.reply_text(
                    welcome_text,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
    except (RuntimeError, ValueError, AttributeError) as e:
        logger.error("Error showing start menu: %s", e)
        # Fallback to new message
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=welcome_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buy command (alternative to button)"""
    if not update.effective_user or not update.message:
        return

    user = update.effective_user
    user_balance = wallet_system.get_user_balance(
        user.id) if wallet_system else 0.00

    # Show loading message
    loading_msg = await update.message.reply_text("🔄 Loading...")

    try:
        if not sms_api:
            await loading_msg.edit_text(
                "❌ Service unavailable",
                parse_mode='HTML'
            )
            return

        # Get available services with pricing for US (country_id=1)
        services_data = await sms_api.get_available_services_for_purchase(country_id=1)

        if not services_data or not services_data.get('success'):
            await loading_msg.edit_text(
                "❌ Unable to load services",
                parse_mode='HTML'
            )
            return

        services = services_data.get('services', [])
        if not services:
            await loading_msg.edit_text(
                "❌ No services available",
                parse_mode='HTML'
            )
            return

        # Build services menu
        keyboard = []
        services_text = f"� <b>US Services</b>\n\n💰 Balance: ${user_balance:.2f}\n\n"

        for service in services[:6]:  # Limit to first 6 services for better UX
            service_id = service.get('id')
            service_name = service.get('name', f'Service {service_id}')
            selling_price = service.get('selling_price', 0)
            recommended = service.get('recommended', False)

            if selling_price > 0:
                emoji = "⭐" if recommended else "📱"

                # Create service selection button
                keyboard.append([
                    InlineKeyboardButton(
                        f"{emoji} {service_name} - ${selling_price:.3f}",
                        callback_data=f"wallet_purchase_{service_id}_{selling_price:.3f}"
                    )
                ])

        keyboard.append([
            InlineKeyboardButton("🔙 Back to Menu", callback_data="start_menu")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await loading_msg.edit_text(services_text, parse_mode='HTML', reply_markup=reply_markup)

    except Exception as e:
        logger.error("Error in buy command: %s", str(e))
        await loading_msg.edit_text(
            "❌ Error loading services",
            parse_mode='HTML'
        )


async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /services command - Browse available services"""
    await buy_command(update, context)


async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /orders command - View order history"""
    if not update.effective_user or not update.message:
        return

    user = update.effective_user

    # Get user orders
    orders = db.get_user_orders(user.id)

    if not orders:
        keyboard = [[
            InlineKeyboardButton(
                "📱 Get Number", callback_data="browse_services"),
            InlineKeyboardButton("🔙 Back", callback_data="start_menu")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📋 <b>Your Orders</b>\n\n"
            "❌ No orders found.\n\n"
            "💡 Use /buy to get your first US phone number!",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return

    # Sort orders by creation date (newest first)
    orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # Limit to last 10 orders for better UX
    recent_orders = orders[:10]

    orders_text = "📋 <b>Recent Orders</b>\n\n"

    for i, order in enumerate(recent_orders, 1):
        status_emoji = {
            'pending': '🟡',
            'processing': '🔄',
            'completed': '✅',
            'timeout': '⏰',
            'refunded': '💰',
            'cancelled': '🚫',
            'error': '❌'
        }

        emoji = status_emoji.get(order['status'], '❔')
        created = datetime.fromisoformat(
            order['created_at']).strftime('%m/%d %H:%M')

        orders_text += (
            f"{emoji} <b>#{order['order_id']}</b>\n"
            f"📱 <code>{order['number']}</code>\n"
            f"💰 ${order['cost']} • {created}\n"
        )

        if order.get('otp'):
            orders_text += f"🔐 Code: <code>{order['otp']}</code>\n"

        orders_text += f"Status: {order['status'].title()}\n\n"

    if len(orders) > 10:
        orders_text += f"... and {len(orders) - 10} more orders\n\n"

    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 Quick Return", callback_data="quick_refund"),
            InlineKeyboardButton("📱 Get More", callback_data="browse_services")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="start_menu")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(orders_text, parse_mode='HTML', reply_markup=reply_markup)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - Service status (admin only)"""
    await service_status_command(update, context)


async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if not update.message:
        return

    help_text = (
        "💬 <b>SMS Verification Service - Complete Guide</b>\n\n"
        "<b>📋 Available Commands</b>\n"
        "• /start - Main dashboard & interface\n"
        "• /buy - Get US phone number instantly\n"
        "• /services - Browse all available services\n"
        "• /deposit - Add wallet credit (min $5)\n"
        "• /balance - Check wallet & transactions\n"
        "• /orders - View complete order history\n"
        "• /refund - Process instant returns\n"
        "• /help - Show this comprehensive guide\n\n"
        "<b>🚀 Quick Start (3 Steps)</b>\n"
        "1️⃣ <b>Add Credit:</b> /deposit → Fund wallet (min $5)\n"
        "2️⃣ <b>Get Number:</b> /buy → Instant US phone\n"
        "3️⃣ <b>Receive SMS:</b> Automatic code delivery\n\n"
        "<b>⚡ How It Works</b>\n"
        "• Add credit → Get number instantly\n"
        "• No confirmations → Fastest experience\n"
        "• Use number for verification immediately\n"
        "• SMS code delivered automatically (up to 10 min)\n"
        "• Instant returns with one click\n\n"
        "<b>🔄 Smart Return Options</b>\n"
        "• ↩️ <b>Return Only:</b> Get money back to wallet\n"
        "• 🔄 <b>Return & Replace:</b> Instant replacement\n"
        "  - Cancels current order automatically\n"
        "  - Uses same service & country settings\n"
        "  - No extra steps or confirmations\n"
        "  - Perfect for getting fresh numbers quickly\n\n"
        "<b>🎯 Interface Features</b>\n"
        "• Enhanced menu bar beside chat input\n"
        "• Comprehensive quick action buttons\n"
        "• One-click credit access\n"
        "• Instant balance checking\n"
        "• Smart return options\n"
        "• Complete order tracking\n"
        "• Transaction history\n"
        "• Automated processing\n\n"
        "<b>📱 Service Information</b>\n"
        "• Primary: Ring4 service (~$0.17)\n"
        "• Backup: Alternative services if unavailable\n"
        "• Multiple countries supported\n"
        "• You'll be notified if backup service is used\n"
        "• Price varies based on availability\n\n"
        "<b>💡 UX Optimizations</b>\n"
        "• Auto-purchase: Click service → Instant delivery\n"
        "• Auto-return: Click return → Instant processing\n"
        "• Smart reorder: One-click number replacement\n"
        "• Auto-cancel: Click cancel → Immediate cancellation\n"
        "• All actions processed automatically\n"
        "• Enhanced menu with all features\n"
        "• Complete workflow optimization\n\n"
        "<b>👨‍💼 Admin Commands</b>\n"
        "• /admin - Admin panel (admin only)\n"
        "• /status - Check service status (admin only)\n\n"
        "🆘 <b>Need help?</b> Contact an administrator.\n"
        "💡 <b>Tip:</b> All features accessible via enhanced menu!"
    )

    await update.message.reply_text(help_text, parse_mode='HTML')


async def contact_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /contact command - Show contact information"""
    if not update.message:
        return

    # Get contact accounts from configuration
    contact_accounts = config_manager.get_contact_accounts()

    if not contact_accounts:
        contact_text = (
            "📞 <b>Contact Us</b>\n\n"
            "❌ Contact information not configured.\n"
            "Please contact an administrator for assistance."
        )
    else:
        # Build contact text with available accounts
        contact_links = []
        for account in contact_accounts:
            if account:  # Make sure account is not empty
                contact_links.append(f"@{account}")

        if contact_links:
            contact_text = (
                "📞 <b>Contact Us</b>\n\n"
                "For enquiries, please get in touch with us through:\n\n"
                f"{'  •  '.join(contact_links)}\n\n"
                "💬 Feel free to reach out for:\n"
                "• Account support\n"
                "• Deposit assistance\n"
                "• Technical issues\n"
                "• General inquiries\n\n"
                "⚡ We typically respond within a few hours!"
            )
        else:
            contact_text = (
                "📞 <b>Contact Us</b>\n\n"
                "❌ Contact information not available.\n"
                "Please contact an administrator for assistance."
            )

    # Create keyboard with back button
    keyboard = [[
        InlineKeyboardButton("🔙 Back to Menu", callback_data="start_menu")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        contact_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

    logger.info("📞 Contact command used by user %s",
                update.effective_user.id if update.effective_user else "Unknown")


async def refund_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /refund command - AUTO-PROCESS without confirmation"""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    # Get user's refundable orders (pending, timeout, error, cancelled) - EXCLUDE already refunded orders
    orders = db.get_user_orders(user_id)
    refundable = [o for o in orders if o['status'] in [
        'pending', 'timeout', 'error', 'cancelled'] and o['status'] != 'refunded']

    if not refundable:
        await update.message.reply_text(
            "💰 <b>No Refundable Orders</b>\n\n"
            "You don't have any orders eligible for refund.\n"
            "Only pending, cancelled, timed out, or error orders can be refunded.",
            parse_mode='HTML'
        )
        return

    keyboard = []
    for order in refundable:
        keyboard.append([
            InlineKeyboardButton(
                f"⚡ Instant Return #{order['order_id']} (${order['cost']})",
                callback_data=f"refund_{order['order_id']}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    refund_text = (
        "⚡ <b>Instant Return System</b>\n\n"
        "Click any order below for immediate automatic return.\n"
        "🚀 <b>No confirmation needed!</b> Credit added to wallet instantly.\n\n"
        f"<b>Returnable Orders:</b> {len(refundable)}\n\n"
        "💡 <b>Process:</b>\n"
        "• Click order → Instant return processed\n"
        "• Credit added to your wallet immediately\n"
        "• Order cancelled automatically\n"
        "• No admin approval required"
    )

    await update.message.reply_text(
        refund_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def admin_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command (admin only)"""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ This command is for administrators only.")
        return

    # Get system statistics
    all_orders = db.orders.all()

    # Count by status
    status_counts = {}
    total_revenue = 0
    auto_refunds_today = 0

    for order in all_orders:
        status = order['status']
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == 'completed':
            try:
                total_revenue += float(order['cost'])
            except (ValueError, TypeError, KeyError):
                pass
        # Count auto refunds from today
        if status == 'refunded':
            try:
                order_date = datetime.fromisoformat(order['created_at']).date()
                if order_date == datetime.now().date():
                    auto_refunds_today += 1
            except (ValueError, TypeError, KeyError):
                pass

    admin_text = (
        f"👨‍💼 <b>Admin Panel</b>\n\n"
        f"📊 <b>System Statistics:</b>\n"
        f"• Total Orders: {len(all_orders)}\n"
        f"• Completed: {status_counts.get('completed', 0)}\n"
        f"• Pending: {status_counts.get('pending', 0)}\n"
        f"• Timeout: {status_counts.get('timeout', 0)}\n"
        f"• Refunded: {status_counts.get('refunded', 0)}\n"
        f"• Errors: {status_counts.get('error', 0)}\n\n"
        f"💰 <b>Revenue:</b> ${total_revenue:.2f}\n"
        f"🔄 <b>Active Polls:</b> {len(active_polls)}\n"
        f"⚡ <b>Auto Refunds Today:</b> {auto_refunds_today}\n\n"
        f"🤖 <b>Bot Status:</b> ✅ Running\n"
        f"🚀 <b>Refund System:</b> ✅ Automatic\n\n"
        f"💡 <b>Note:</b> All refunds are now processed automatically.\n"
        f"Admin approval only required for wallet deposits."
    )

    await update.message.reply_text(admin_text, parse_mode='HTML')


async def balance_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command - Show user's wallet balance and recent transactions"""
    # Handle both direct messages and callback queries
    if update.callback_query:
        query = update.callback_query
        user = query.from_user
        await query.answer()
        send_method = query.edit_message_text
    elif update.message:
        user = update.effective_user
        send_method = update.message.reply_text
    else:
        return

    if not user:
        return
    user_id = user.id

    if not wallet_system:
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Wallet system not available.")
        elif update.message:
            await update.message.reply_text("❌ Wallet system not available.")
        return

    try:
        # Get wallet summary
        wallet_summary = wallet_system.get_wallet_summary(user_id)

        # Format balance information
        balance_text = (
            f"💰 <b>Your Wallet Balance</b>\n\n"
            f"💵 <b>Current Balance:</b> ${wallet_summary['balance']:.2f}\n\n"
            f"📊 <b>Statistics:</b>\n"
            f"• Total Deposited: ${wallet_summary['total_deposited']:.2f}\n"
            f"• Total Spent: ${wallet_summary['total_spent']:.2f}\n"
            f"• Total Refunded: ${wallet_summary['total_refunded']:.2f}\n\n"
        )

        # Add recent transactions
        recent_transactions = wallet_summary['recent_transactions']
        if recent_transactions:
            balance_text += "📊 <b>Recent Transactions:</b>\n"
            for tx in recent_transactions[:5]:  # Show last 5 transactions
                tx_type_emoji = {
                    'deposit': '💰',
                    'deduction': '💸',
                    'refund': '💫',
                    'admin_credit': '🎁'
                }
                emoji = tx_type_emoji.get(tx['transaction_type'], '📄')
                amount_sign = '+' if tx['transaction_type'] in [
                    'deposit', 'refund', 'admin_credit'] else '-'

                # Format timestamp
                tx_time = datetime.fromisoformat(
                    tx['timestamp']).strftime('%m/%d %H:%M')

                balance_text += (
                    f"{emoji} {amount_sign}${tx['amount']:.2f} - {tx['description'][:30]}{'...' if len(tx['description']) > 30 else ''}\n"
                    f"   <i>{tx_time} | Balance: ${tx['balance_after']:.2f}</i>\n"
                )
        else:
            balance_text += "📝 <b>No transactions yet</b>\n"

        # Add action buttons
        keyboard = []

        # Add deposit button if balance is low
        if wallet_summary['balance'] < 5.00:
            keyboard.append([
                InlineKeyboardButton(
                    "💵 Add Credit (Min: $5)", callback_data="deposit_funds")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("💰 Add More Funds",
                                     callback_data="deposit_funds")
            ])

        keyboard.append([
            InlineKeyboardButton("🔍 Explore Services",
                                 callback_data="browse_services"),
            InlineKeyboardButton(
                "📊 Full History", callback_data="transaction_history")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await send_method(
            balance_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        logger.info(
            "💰 Balance checked by user %s: $%.2f", user_id, wallet_summary['balance'])

    except RuntimeError as e:
        logger.error("❌ Error showing balance for user %s: %s",
                     user_id, str(e))
        error_msg = "❌ Error retrieving balance information. Please try again."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        elif update.message:
            await update.message.reply_text(error_msg)


async def deposit_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /deposit command - Direct access to deposit funds"""
    if not update.effective_user or not update.message:
        return

    user = update.effective_user
    user_balance = wallet_system.get_user_balance(
        user.id) if wallet_system else 0.00

    if not wallet_system:
        await update.message.reply_text(
            "❌ <b>Wallet system not available</b>\n\n"
            "Please contact an administrator.",
            parse_mode='HTML'
        )
        return

    # Show deposit method options with inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("� Deposit via Wallet Address",
                                 callback_data="deposit_method_wallet"),
        ],
        [
            InlineKeyboardButton("� Deposit via Binance (Binance ID)",
                                 callback_data="deposit_method_binance")
        ],
        [
            InlineKeyboardButton("💰 Check Wallet",
                                 callback_data="show_balance")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    deposit_text = (
        f"💵 <b>Choose Deposit Method</b>\n\n"
        f"💰 <b>Current Balance:</b> ${user_balance:.2f}\n\n"
        f"Select your preferred deposit method:\n\n"
        f"� <b>Wallet Address:</b> Traditional crypto transfer\n"
        f"🟡 <b>Binance Transfer:</b> Lower fees via Binance ID\n\n"
        f"📊 <b>Amount Range:</b> ${wallet_system.MIN_DEPOSIT_USD:.2f} - ${wallet_system.MAX_DEPOSIT_USD:.2f}\n\n"
        f"🔒 Both methods require admin verification for security"
    )

    await update.message.reply_text(
        deposit_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

    logger.info("💰 Deposit command used by user %s (balance: $%.2f)",
                user.id, user_balance)


async def approve_refund_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /approve_refund command (admin only) - Approve specific refund requests"""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ This command is for administrators only.")
        return

    # Extract order ID from command arguments
    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ Please provide an order ID.\n"
            "Usage: /approve_refund <order_id>"
        )
        return

    order_id = args[0]  # Keep as string, don't convert to int

    # Check if refund request exists
    pending_refunds = db.get_pending_refunds()
    refund_request = None
    for refund in pending_refunds:
        if refund.get('order_id') == order_id:
            refund_request = refund
            break

    if not refund_request:
        await update.message.reply_text(f"❌ No pending refund request found for order ID {order_id}.")
        return

    # Get the original order
    order = db.get_order(order_id)
    if not order:
        await update.message.reply_text(f"❌ Order {order_id} not found in database.")
        return

    try:
        # Process the refund
        db.update_refund_status(order_id, 'approved', user_id)
        db.update_order_status(order_id, 'refunded')

        # Cancel the order with SMSPool if API is available
        if sms_api and order.get('order_id'):
            cancel_result = await sms_api.cancel_order(str(order['order_id']))
            if cancel_result.get('success'):
                logger.info(
                    "✅ Order %s cancelled with SMS Bot", order['order_id'])
            else:
                logger.warning(
                    "⚠️ Failed to cancel order %s with SMS Bot: %s", order['order_id'], cancel_result.get('message'))

        # Notify the user
        try:
            await context.bot.send_message(
                chat_id=refund_request['user_id'],
                text=(
                    f"✅ <b>Refund Approved</b>\n\n"
                    f"Your refund request for order #{order_id} has been approved.\n"
                    f"Amount: ${order.get('cost', 'N/A')}\n\n"
                    f"The refund will be processed according to our refund policy."
                ),
                parse_mode='HTML'
            )
        except RuntimeError as notify_error:
            logger.error(
                "❌ Failed to notify user %s about refund approval: %s", refund_request['user_id'], notify_error)

        await update.message.reply_text(
            f"✅ <b>Refund Approved</b>\n\n"
            f"Order ID: {order_id}\n"
            f"User ID: {refund_request['user_id']}\n"
            f"Amount: ${order.get('cost', 'N/A')}\n"
            f"Approved by: {update.effective_user.first_name}\n\n"
            f"User has been notified automatically.",
            parse_mode='HTML'
        )

        logger.info(
            "✅ Refund approved for order %s by admin %s", order_id, user_id)

    except RuntimeError as e:
        logger.error(
            "❌ Error processing refund approval for order %s: %s", order_id, str(e))
        await update.message.reply_text(
            f"❌ Error processing refund approval: {str(e)}\n"
            "Please try again or contact system administrator."
        )


async def service_status_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /services command (admin only) - Check service availability and pricing"""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ This command is for administrators only.")
        return

    if not sms_api:
        await update.message.reply_text("❌ SMS API not initialized.")
        return

    # Show loading message
    loading_msg = await update.message.reply_text("🔄 Checking service availability and pricing...")

    try:
        # Get pricing for all services
        pricing_info = await sms_api.get_service_pricing()

        if not pricing_info.get('success'):
            await loading_msg.edit_text("❌ Failed to get service pricing information.")
            return

        # Build status message
        status_text = "📊 <b>Service Status & Pricing</b>\n\n"

        # Ring4 specific status
        ring4_status = pricing_info.get('ring4_status')
        if ring4_status:
            status_icon = "✅" if ring4_status['available'] else "❌"
            status_text += f"{status_icon} <b>Ring4 (Primary):</b> "
            if ring4_status['available']:
                status_text += f"${ring4_status['price']}\n"
            else:
                status_text += "Unavailable\n"

        status_text += "\n<b>Alternative Services:</b>\n"

        # Show all services
        for service in pricing_info.get('all_services', []):
            if service['id'] == 1574:  # Skip Ring4 as we already showed it
                continue

            status_icon = "✅" if service['available'] else "❌"
            status_text += f"{status_icon} {service['name']}: "
            if service['available']:
                status_text += f"${service['price']}\n"
            else:
                status_text += "Unavailable\n"

        # Show cheapest available
        cheapest = pricing_info.get('cheapest_available')
        if cheapest:
            status_text += f"\n💰 <b>Cheapest Available:</b> {cheapest['name']} (${cheapest['price']})\n"

        # Show recommendations
        available_count = len(pricing_info.get('available_services', []))
        status_text += "\n📈 <b>Summary:</b>\n"
        status_text += f"• Available services: {available_count}/4\n"

        if ring4_status and not ring4_status['available']:
            if cheapest:
                # Expected Ring4 price
                price_diff = float(cheapest['price']) - 0.17
                status_text += f"• Price impact: +${price_diff:.2f} per order\n"
                status_text += "• Recommend adjusting user pricing or waiting for Ring4\n"
        else:
            status_text += "• Ring4 available: No pricing adjustments needed\n"

        await loading_msg.edit_text(status_text, parse_mode='HTML')

        logger.info("✅ Service status checked by admin %s", user_id)

    except RuntimeError as e:
        logger.error("❌ Error checking service status: %s", str(e))
        await loading_msg.edit_text(
            f"❌ Error checking service status: {str(e)}\n"
            "Please try again later."
        )


async def handle_deposit_funds(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit funds request - Show deposit method options"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    if not wallet_system:
        await query.edit_message_text("❌ Wallet system not available.")
        return

    # Show deposit method options
    keyboard = [
        [
            InlineKeyboardButton("� Deposit via Wallet Address",
                                 callback_data="deposit_method_wallet"),
        ],
        [
            InlineKeyboardButton("� Deposit via Binance (Binance ID)",
                                 callback_data="deposit_method_binance")
        ],
        [
            InlineKeyboardButton("🔙 Back to Balance",
                                 callback_data="show_balance")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    deposit_text = (
        f"💵 <b>Choose Deposit Method</b>\n\n"
        f"Select your preferred deposit method:\n\n"
        f"� <b>Wallet Address:</b> Traditional crypto transfer\n"
        f"� <b>Binance Transfer:</b> Lower fees via Binance ID\n\n"
        f"Both methods require admin verification for security."
    )

    await query.edit_message_text(
        deposit_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def handle_deposit_method_wallet(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle wallet address deposit method selection"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    if not wallet_system:
        await query.edit_message_text("❌ Wallet system not available.")
        return

    # Show deposit amount options for wallet method
    keyboard = [
        [
            InlineKeyboardButton("💰 $5.00 (Minimum)",
                                 callback_data="deposit_wallet_5.00"),
            InlineKeyboardButton(
                "💰 $10.00", callback_data="deposit_wallet_10.00")
        ],
        [
            InlineKeyboardButton(
                "💰 $25.00", callback_data="deposit_wallet_25.00"),
            InlineKeyboardButton(
                "💰 $50.00", callback_data="deposit_wallet_50.00")
        ],
        [
            InlineKeyboardButton(
                "💰 $100.00", callback_data="deposit_wallet_100.00"),
            InlineKeyboardButton(
                "🔢 Custom", callback_data="deposit_wallet_custom")
        ],
        [
            InlineKeyboardButton("🔙 Back to Methods",
                                 callback_data="deposit_funds")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    deposit_text = (
        f"💳 <b>Wallet Address Deposit</b>\n\n"
        f"Choose deposit amount:\n\n"
        f"💡 <b>Benefits:</b>\n"
        f"• Works with any crypto wallet\n"
        f"• Traditional transfer method\n"
        f"• Automatic refunds to wallet\n"
        f"• Complete transaction history\n\n"
        f"📊 <b>Amount Range</b>\n"
        f"• Minimum: ${wallet_system.MIN_DEPOSIT_USD:.2f}\n"
        f"• Maximum: ${wallet_system.MAX_DEPOSIT_USD:.2f}\n\n"
        f"🔒 All deposits require admin verification for security"
    )

    await query.edit_message_text(
        deposit_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def handle_deposit_method_binance(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle Binance transfer deposit method selection"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    if not wallet_system:
        await query.edit_message_text("❌ Wallet system not available.")
        return

    # Show deposit amount options for Binance method
    keyboard = [
        [
            InlineKeyboardButton("💰 $5.00 (Minimum)",
                                 callback_data="deposit_binance_5.00"),
            InlineKeyboardButton(
                "💰 $10.00", callback_data="deposit_binance_10.00")
        ],
        [
            InlineKeyboardButton(
                "💰 $25.00", callback_data="deposit_binance_25.00"),
            InlineKeyboardButton(
                "💰 $50.00", callback_data="deposit_binance_50.00")
        ],
        [
            InlineKeyboardButton(
                "💰 $100.00", callback_data="deposit_binance_100.00"),
            InlineKeyboardButton(
                "🔢 Custom", callback_data="deposit_binance_custom")
        ],
        [
            InlineKeyboardButton("🔙 Back to Methods",
                                 callback_data="deposit_funds")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    deposit_text = (
        f"🟡 <b>Binance Transfer Deposit</b>\n\n"
        f"Choose deposit amount:\n\n"
        f"💡 <b>Benefits:</b>\n"
        f"• Lower transaction fees\n"
        f"• Faster processing\n"
        f"• Binance to Binance transfer\n"
        f"• Complete transaction history\n\n"
        f"📊 <b>Amount Range</b>\n"
        f"• Minimum: ${wallet_system.MIN_DEPOSIT_USD:.2f}\n"
        f"• Maximum: ${wallet_system.MAX_DEPOSIT_USD:.2f}\n\n"
        f"🔒 All deposits require admin verification for security"
    )

    await query.edit_message_text(
        deposit_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def handle_deposit_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom deposit amount request"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    # Ask user to send custom amount
    custom_text = (
        f"💰 <b>Custom Deposit Amount</b>\n\n"
        f"💡 Please send your desired deposit amount as a message.\n\n"
        f"<b>Requirements:</b>\n"
        f"• Minimum: ${wallet_system.MIN_DEPOSIT_USD if wallet_system else 5.00}\n"
        f"• Format: Enter amount only (e.g., 10.50)\n"
        f"• No symbols ($ or USD)\n\n"
        f"📝 <b>Example:</b> Send \"10.50\" for $10.50\n\n"
        f"❌ Send /cancel to abort"
    )

    keyboard = [[
        InlineKeyboardButton("❌ Cancel", callback_data="deposit_funds")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        custom_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

    # Set user state to expect custom amount
    if context.user_data is not None:
        context.user_data['awaiting_deposit_amount'] = True
    logger.info("💰 User %s requested custom deposit amount", user.id)


async def handle_deposit_amount(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit amount selection"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    if not wallet_system:
        await query.edit_message_text("❌ Wallet system not available.")
        return

    try:
        # Extract amount from callback data
        callback_data = query.data
        if not callback_data:
            await query.edit_message_text("❌ Invalid callback data.")
            return

        if callback_data.startswith("deposit_amount_"):
            amount = float(callback_data.split("_")[-1])
        else:
            await query.edit_message_text("❌ Invalid amount selection.")
            return

        # Create deposit request
        deposit_request = wallet_system.create_deposit_request(
            user_id=user.id,
            amount=amount,
            binance_wallet=BINANCE_WALLET
        )

        # Format deposit instructions
        instructions_text = "💰 <b>Wallet Deposit Request</b>\n\n"
        instructions_text += "\n".join(deposit_request['instructions'])

        keyboard = [[
            InlineKeyboardButton(
                "✅ Payment Sent", callback_data=f"deposit_sent_{deposit_request['deposit_id']}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_deposit")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            instructions_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        logger.info("💰 Deposit request created for user %s: $%s",
                    user.id, amount)

    except ValueError as e:
        await query.edit_message_text(
            f"❌ <b>Invalid Deposit Amount</b>\n\n"
            f"Error: {str(e)}\n\n"
            f"Please try again with a valid amount.",
            parse_mode='HTML'
        )
    except RuntimeError as e:
        logger.error("❌ Error creating deposit request: %s", str(e))
        await query.edit_message_text(
            "❌ Error creating deposit request. Please try again."
        )


async def handle_deposit_wallet_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle wallet deposit amount selection"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    if not wallet_system:
        await query.edit_message_text("❌ Wallet system not available.")
        return

    try:
        # Extract amount from callback data
        callback_data = query.data
        if not callback_data:
            await query.edit_message_text("❌ Invalid callback data.")
            return

        if callback_data.startswith("deposit_wallet_"):
            amount_str = callback_data.split("_")[-1]
            if amount_str == "custom":
                # Redirect to dedicated custom handler
                await handle_deposit_wallet_custom(update, context)
                return

            amount = float(amount_str)
        else:
            await query.edit_message_text("❌ Invalid amount selection.")
            return

        # Create deposit request for wallet method
        deposit_request = wallet_system.create_deposit_request(
            user_id=user.id,
            amount=amount,
            binance_wallet=BINANCE_WALLET
        )

        # Format deposit instructions
        instructions_text = "💳 <b>Wallet Deposit Request</b>\n\n"
        instructions_text += "\n".join(deposit_request['instructions'])

        keyboard = [[
            InlineKeyboardButton(
                "✅ Payment Sent", callback_data=f"deposit_sent_{deposit_request['deposit_id']}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_deposit")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            instructions_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        logger.info("💳 Wallet deposit request created for user %s: $%s",
                    user.id, amount)

    except ValueError as e:
        await query.edit_message_text(
            f"❌ <b>Invalid Deposit Amount</b>\n\n"
            f"Error: {str(e)}\n\n"
            f"Please try again with a valid amount.",
            parse_mode='HTML'
        )
    except RuntimeError as e:
        logger.error("❌ Error creating wallet deposit request: %s", str(e))
        await query.edit_message_text(
            "❌ Error creating deposit request. Please try again."
        )


async def handle_deposit_binance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Binance deposit amount selection"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    if not wallet_system:
        await query.edit_message_text("❌ Wallet system not available.")
        return

    try:
        # Extract amount from callback data
        callback_data = query.data
        if not callback_data:
            await query.edit_message_text("❌ Invalid callback data.")
            return

        if callback_data.startswith("deposit_binance_"):
            amount_str = callback_data.split("_")[-1]
            if amount_str == "custom":
                # Redirect to dedicated custom handler
                await handle_deposit_binance_custom(update, context)
                return

            amount = float(amount_str)
        else:
            await query.edit_message_text("❌ Invalid amount selection.")
            return

        # Create Binance deposit request
        if not BINANCE_ID:
            await query.edit_message_text(
                "❌ <b>Binance ID Not Configured</b>\n\n"
                "Please contact administrator to set up Binance transfers.",
                parse_mode='HTML'
            )
            return

        # Use wallet system to create Binance deposit request
        deposit_request = wallet_system.create_binance_deposit_request(
            user_id=user.id,
            amount=amount,
            binance_id=BINANCE_ID
        )

        # Format deposit instructions
        instructions_text = (
            f"🟡 <b>Binance Transfer Instructions</b>\n\n"
            f"💰 <b>Amount:</b> ${amount:.2f} USDT\n\n"
            f"Please make the payment via Binance (Binance to Binance transfer) to minimize transaction fees.\n\n"
            f"🆔 <b>My Binance ID:</b> <code>{BINANCE_ID}</code>\n\n"
            f"📋 <b>Instructions:</b>\n"
            f"1. Open Binance app/website\n"
            f"2. Go to Pay → Transfer\n"
            f"3. Enter Binance ID: <code>{BINANCE_ID}</code>\n"
            f"4. Send exactly <b>${amount:.2f} USDT</b>\n"
            f"5. Copy the Transaction ID (TXID)\n"
            f"6. Click 'Payment Sent' below\n\n"
            f"⚠️ <b>Important:</b>\n"
            f"• Send exactly the specified amount\n"
            f"• Use USDT (Tether USD)\n"
            f"• Save your transaction receipt\n\n"
            f"After payment, please enter your Transaction ID (TXID) or upload a screenshot.\n"
            f"Once admin verifies, your balance will be credited.\n\n"
            f"🆔 <b>Deposit ID:</b> <code>{deposit_request['deposit_id']}</code>"
        )

        keyboard = [[
            InlineKeyboardButton(
                "✅ Payment Sent", callback_data=f"binance_sent_{deposit_request['deposit_id']}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_deposit")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            instructions_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        logger.info("🟡 Binance deposit request created for user %s: $%s (ID: %s)",
                    user.id, amount, deposit_request['deposit_id'])

    except ValueError as e:
        await query.edit_message_text(
            f"❌ <b>Invalid Deposit Amount</b>\n\n"
            f"Error: {str(e)}\n\n"
            f"Please try again with a valid amount.",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error("❌ Error creating Binance deposit request: %s", str(e))
        await query.edit_message_text(
            "❌ Error creating deposit request. Please try again."
        )


async def handle_deposit_wallet_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom wallet deposit amount request"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    # Ask user to send custom amount for wallet deposit
    custom_text = (
        f"💳 <b>Custom Wallet Deposit Amount</b>\n\n"
        f"💡 Please send your desired deposit amount as a message.\n\n"
        f"<b>Requirements:</b>\n"
        f"• Minimum: ${wallet_system.MIN_DEPOSIT_USD if wallet_system else 5.00}\n"
        f"• Maximum: ${wallet_system.MAX_DEPOSIT_USD if wallet_system else 1000.00}\n"
        f"• Format: Enter amount only (e.g., 10.50)\n"
        f"• No symbols ($ or USD)\n\n"
        f"📝 <b>Example:</b> Send \"10.50\" for $10.50\n\n"
        f"💳 <b>Payment Method:</b> Wallet Transfer\n"
        f"🏦 <b>Wallet:</b> <code>{BINANCE_WALLET}</code>\n\n"
        f"❌ Send /cancel to abort"
    )

    keyboard = [[
        InlineKeyboardButton("❌ Cancel", callback_data="deposit_method_wallet")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        custom_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

    # Set user state to expect custom wallet amount
    if context.user_data is not None:
        context.user_data['awaiting_deposit_amount'] = True
        context.user_data['deposit_method'] = 'wallet'
    logger.info("💳 User %s requested custom wallet deposit amount", user.id)


async def handle_deposit_binance_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom Binance deposit amount request"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    # Ask user to send custom amount for Binance deposit
    custom_text = (
        f"🟡 <b>Custom Binance Deposit Amount</b>\n\n"
        f"💡 Please send your desired deposit amount as a message.\n\n"
        f"<b>Requirements:</b>\n"
        f"• Minimum: ${wallet_system.MIN_DEPOSIT_USD if wallet_system else 5.00}\n"
        f"• Maximum: ${wallet_system.MAX_DEPOSIT_USD if wallet_system else 1000.00}\n"
        f"• Format: Enter amount only (e.g., 10.50)\n"
        f"• No symbols ($ or USD)\n\n"
        f"📝 <b>Example:</b> Send \"10.50\" for $10.50\n\n"
        f"🟡 <b>Payment Method:</b> Binance Transfer\n"
        f"🆔 <b>Binance ID:</b> <code>{BINANCE_ID}</code>\n\n"
        f"❌ Send /cancel to abort"
    )

    keyboard = [[
        InlineKeyboardButton(
            "❌ Cancel", callback_data="deposit_method_binance")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        custom_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

    # Set user state to expect custom Binance amount
    if context.user_data is not None:
        context.user_data['awaiting_deposit_amount'] = True
        context.user_data['deposit_method'] = 'binance'
    logger.info("🟡 User %s requested custom Binance deposit amount", user.id)


async def handle_wallet_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle wallet purchase callback (e.g., wallet_purchase_1574_0.15)"""
    query = update.callback_query
    user = update.effective_user

    if not query or not user or not query.data:
        return

    await query.answer()

    try:
        # Parse callback data: wallet_purchase_1574_0.15
        parts = query.data.split('_')
        if len(parts) >= 3:
            service_id = int(parts[2])
            selling_price = float(parts[3]) if len(parts) > 3 else 0.15
        else:
            # Default fallback
            service_id = 1574  # Ring4
            selling_price = 0.15

        # Get service name
        service_names = {1574: 'Ring4', 22: 'Telegram',
                         395: 'Google', 1012: 'WhatsApp'}
        service_name = service_names.get(service_id, f'Service {service_id}')

        # Store selection in user context for the purchase process
        if context.user_data is not None:
            context.user_data['selected_service_id'] = service_id
            context.user_data['selected_price'] = selling_price

        # Process the service purchase with the selected parameters
        await handle_service_purchase(update, context, service_id, service_name, selling_price)

        logger.info("✅ Wallet purchase callback processed: user %s, service %s, price $%.2f",
                    user.id, service_name, selling_price)

    except (ValueError, IndexError) as e:
        logger.error(
            "❌ Error parsing wallet purchase callback %s: %s", query.data, str(e))
        await query.edit_message_text(
            "❌ <b>Invalid Purchase Request</b>\n\n"
            "The purchase request format is invalid. Please try again.",
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error("❌ Error in wallet purchase callback: %s", str(e))
        await query.edit_message_text(
            "❌ <b>Purchase Error</b>\n\n"
            "An error occurred while processing your purchase. Please try again.",
            parse_mode='HTML'
        )


async def handle_service_purchase_with_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle service purchase using wallet balance"""
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    try:
        # Extract service info from callback data
        callback_data = query.data
        if not callback_data:
            logger.error("❌ No callback data received")
            return

        parts = callback_data.split('_')
        service_id = int(parts[2])
        selling_price = float(parts[3])

        # Get service name
        service_names = {1574: 'Ring4', 22: 'Telegram',
                         395: 'Google', 1012: 'WhatsApp'}
        service_name = service_names.get(service_id, f'Service {service_id}')

        # Check wallet balance
        if not wallet_system:
            await query.edit_message_text(
                "❌ Wallet system not available. Please try again later.",
                parse_mode='HTML'
            )
            return

        user_balance = wallet_system.get_user_balance(user.id)

        if user_balance < selling_price:
            # Insufficient balance - show deposit options
            needed_amount = selling_price - user_balance

            keyboard = [
                [InlineKeyboardButton(
                    "💰 Add Funds", callback_data="deposit_funds")],
                [InlineKeyboardButton(
                    "🔙 Back to Services", callback_data="browse_services")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"💰 <b>Insufficient Wallet Balance</b>\n\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"💵 <b>Price:</b> ${selling_price:.2f}\n"
                f"💰 <b>Your Balance:</b> ${user_balance:.2f}\n"
                f"❌ <b>Needed:</b> ${needed_amount:.2f}\n\n"
                f"Please add funds to your wallet to continue.",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return

        # Sufficient balance - proceed with purchase
        await query.edit_message_text(
            f"🔄 <b>Processing {service_name} Purchase</b>\n\n"
            f"💰 <b>Price:</b> ${selling_price:.2f}\n"
            f"💰 <b>Wallet Balance:</b> ${user_balance:.2f}\n"
            f"📱 <b>Service:</b> {service_name}\n\n"
            f"⚡ Purchasing your US number...",
            parse_mode='HTML'
        )

        # Process the purchase
        await process_wallet_purchase(user.id, context, query.edit_message_text, service_id, service_name, selling_price)

    except RuntimeError as e:
        logger.error("❌ Error in wallet-based service purchase: %s", str(e))
        await query.edit_message_text(
            "❌ Error processing purchase. Please try again.",
            parse_mode='HTML'
        )


async def process_wallet_purchase(user_id: int, context: ContextTypes.DEFAULT_TYPE, send_method, service_id: int, service_name: str, selling_price: float):
    """Process service purchase using wallet balance"""

    purchase_logger.info(
        "🚀 Starting wallet purchase for user %s: %s ($%.2f)", user_id, service_name, selling_price)

    start_time = asyncio.get_event_loop().time()
    order_id = None

    # Get country information from context if available
    country_id = context.user_data.get(
        'selected_country_id', 1) if context.user_data else 1  # Default to US
    country_name = "United States"
    country_flag = "🇺🇸"

    # Try to get country details from SMS API
    if sms_api and country_id:
        try:
            country = sms_api.get_country_by_id(country_id)
            if country:
                country_name = country.get("name", country_name)
                country_flag = country.get("flag", country_flag)
        except Exception as e:
            logger.warning(
                f"⚠️ Could not get country details for ID {country_id}: {e}")

    try:
        # Step 1: Reserve wallet balance (don't deduct yet - only when OTP received)
        if not wallet_system:
            await send_method(
                "❌ Wallet system not available. Please try again later.",
                parse_mode='HTML'
            )
            return

        # Generate order ID for reservation
        order_id = f"ORD_{user_id}_{int(datetime.now().timestamp())}"

        reservation_success = wallet_system.reserve_balance(
            user_id=user_id,
            amount=selling_price,
            order_id=order_id,
            description=f"{service_name} service purchase ({country_name})"
        )

        if not reservation_success:
            user_balance = wallet_system.get_user_balance(user_id)
            await send_method(
                f"❌ <b>Insufficient Balance</b>\n\n"
                f"💰 Service Cost: ${selling_price:.2f}\n"
                f"💰 Your Balance: ${user_balance:.2f}\n"
                f"💸 Need: ${selling_price - user_balance:.2f} more\n\n"
                f"Please add funds to your wallet.",
                parse_mode='HTML'
            )
            return

        # Step 2: Purchase the SMS number
        if not sms_api:
            # Cancel the reservation if SMS API is not available
            wallet_system.cancel_reservation(
                user_id=user_id,
                amount=selling_price,
                order_id=order_id,
                reason="SMS API unavailable"
            )
            await send_method(
                f"❌ <b>Service Unavailable</b>\n\n"
                f"SMS service is currently unavailable.\n"
                f"No charge to your wallet.",
                parse_mode='HTML'
            )
            return

        # Show processing message (no charge yet)
        current_balance = wallet_system.get_user_balance(user_id)
        await send_method(
            f"🔄 <b>Processing {service_name} Purchase</b>\n\n"
            f"💰 <b>Cost:</b> ${selling_price:.2f} (reserved)\n"
            f"💰 <b>Wallet Balance:</b> ${current_balance:.2f}\n"
            f"📱 <b>Service:</b> {service_name}\n"
            f"🌍 <b>Country:</b> {country_flag} {country_name}\n\n"
            f"🔄 Acquiring your number...\n\n"
            f"💡 <b>Note:</b> You'll only be charged when you receive the OTP code!",
            parse_mode='HTML'
        )

        # Purchase the SMS number with country support
        purchase_result = await sms_api.purchase_specific_service(
            service_id=service_id,
            service_name=service_name,
            country_id=country_id
        )

        if not purchase_result.get('success'):
            # Cancel the reservation
            wallet_system.cancel_reservation(
                user_id=user_id,
                amount=selling_price,
                order_id=order_id,
                reason=f"Purchase failed - {purchase_result.get('error', 'Purchase failed')}"
            )

            await send_method(
                f"❌ <b>Purchase Failed</b>\n\n"
                f"Error: {purchase_result.get('error', 'Unknown error')}\n"
                f"💰 No charge to your wallet.\n\n"
                f"Please try again or contact support.",
                parse_mode='HTML'
            )
            return

        # Success - create order record (but don't charge yet)
        actual_order_id = purchase_result.get('order_id', order_id)
        phone_number = purchase_result.get('number')
        actual_cost = purchase_result.get('cost', selling_price)

        # Create order in database with complete information
        order_data = {
            'order_id': actual_order_id,
            'number': phone_number,
            'cost': selling_price,  # What user will pay when OTP received
            'actual_cost': actual_cost,  # What SMS provider charged
            'service_name': service_name,
            'service_id': service_id,
            'country_id': country_id,
            'country_name': country_name,
            'country_flag': country_flag,
            'reservation_order_id': order_id  # Track our reservation
        }

        db.create_order(user_id, order_data)

        # Send success message with number (not charged yet)
        total_time = asyncio.get_event_loop().time() - start_time
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔄 Get Different Number", callback_data=f"instant_refund_reorder_{actual_order_id}"),
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel Order", callback_data=f"cancel_order_{actual_order_id}"),
                InlineKeyboardButton(
                    "💰 Check Balance", callback_data="show_balance")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await send_method(
            f"🎉 <b>{service_name} Number Acquired!</b>\n\n"
            f"📱 <b>Your Number:</b> <code>{phone_number}</code>\n"
            f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
            f"💰 <b>Cost:</b> ${selling_price:.2f} (reserved - will charge when OTP received)\n"
            f"💰 <b>Wallet Balance:</b> ${current_balance:.2f}\n"
            f"🆔 <b>Order ID:</b> <code>{actual_order_id}</code>\n\n"
            f"⏰ <b>Valid for 10 minutes</b>\n"
            f"🔄 <b>OTP monitoring started</b>\n\n"
            f"⚡ <i>Acquired in {total_time:.1f} seconds</i>\n\n"
            f"💡 <b>Payment:</b> You'll only be charged when you receive the OTP code!\n"
            f"Use this number for verification. You'll get the OTP automatically!",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        # Start OTP polling if order_id is valid
        if actual_order_id:
            start_otp_polling(actual_order_id, user_id, context)
        else:
            logger.warning("⚠️ No order_id available for OTP polling")

        purchase_logger.info(
            "✅ Number acquired for user %s: %s (%s) - Payment reserved, will charge on OTP", user_id, actual_order_id, country_name)

    except RuntimeError as e:
        total_time = asyncio.get_event_loop().time() - start_time
        purchase_logger.error(
            "❌ Exception during wallet purchase for user %s after %.2fs: %s", user_id, total_time, str(e))

        # Try to cancel reservation if we made one
        if 'order_id' in locals() and order_id and wallet_system:
            try:
                wallet_system.cancel_reservation(
                    user_id=user_id,
                    amount=selling_price,
                    order_id=order_id,
                    reason=f"Exception during purchase: {str(e)[:50]}"
                )
            except RuntimeError as cancel_error:
                logger.error("❌ Failed to cancel reservation for user %s: %s",
                             user_id, cancel_error)

        await send_method(
            f"❌ <b>Purchase Error</b>\n\n"
            f"An error occurred during purchase.\n"
            f"💰 No charge to your wallet.\n\n"
            f"Please try again or contact support if the issue persists.",
            parse_mode='HTML'
        )


async def handle_deposit_sent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user claims deposit is sent"""
    query = update.callback_query
    if not query or not query.from_user:
        return

    # Extract deposit ID from callback data: "deposit_sent_DEP_123456789_1754854768"
    if not query.data:
        await query.answer("❌ Invalid request.")
        return

    # Get "DEP_123456789_1754854768"
    deposit_id = "_".join(query.data.split('_')[2:])
    user = query.from_user

    await query.answer()

    # Get deposit details to show amount to admins
    if not wallet_system:
        await query.edit_message_text("❌ Wallet system not available.")
        return

    deposit = wallet_system.get_deposit_status(deposit_id)
    if not deposit:
        await query.edit_message_text("❌ Deposit not found or expired.")
        return

    amount = deposit['amount_usd']

    # Notify all admins about deposit claim
    for admin_id in ADMIN_IDS:
        try:
            keyboard = [[
                InlineKeyboardButton(
                    f"✅ Approve ${amount:.2f}", callback_data=f"approve_deposit_{deposit_id}"),
                InlineKeyboardButton(
                    f"❌ Deny ${amount:.2f}", callback_data=f"deny_deposit_{deposit_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"💰 <b>New Deposit Claim</b>\n\n"
                    f"👤 <b>User:</b> {user.id} (@{user.username or 'Unknown'})\n"
                    f"💰 <b>Amount:</b> ${amount:.2f}\n"
                    f"🆔 <b>Deposit ID:</b> <code>{deposit_id}</code>\n"
                    f"💳 <b>Method:</b> Wallet Address\n\n"
                    f"⚠️ <b>Action Required:</b> Verify payment and approve/deny"
                ),
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        except RuntimeError as e:
            logger.error("Failed to notify admin %s: %s", admin_id, e)

    await query.edit_message_text(
        f"✅ <b>Deposit Claim Submitted</b>\n\n"
        f"🆔 <b>Deposit ID:</b> <code>{deposit_id}</code>\n\n"
        f"👨‍💼 Admins have been notified and will verify your payment.\n"
        f"⏰ You'll be notified once the deposit is approved.\n\n"
        f"💡 <b>Note:</b> Only send the exact amount to avoid delays.",
        parse_mode='HTML'
    )

    logger.info("💰 Deposit claim submitted by user %s: %s",
                user.id, deposit_id)


async def handle_binance_deposit_sent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user claims Binance deposit is sent"""
    query = update.callback_query
    if not query or not query.from_user:
        return

    # Extract deposit ID from callback data: "binance_sent_BIN_123456789_1754854768"
    if not query.data:
        await query.answer("❌ Invalid request.")
        return

    # Get "BIN_123456789_1754854768"
    deposit_id = "_".join(query.data.split('_')[2:])
    user = query.from_user

    await query.answer()

    # Get deposit details to show amount to admins
    if not wallet_system:
        await query.edit_message_text("❌ Wallet system not available.")
        return

    deposit = wallet_system.get_deposit_status(deposit_id)
    if not deposit:
        await query.edit_message_text("❌ Deposit not found or expired.")
        return

    amount = deposit['amount_usd']

    # Notify all admins about Binance deposit claim
    for admin_id in ADMIN_IDS:
        try:
            keyboard = [[
                InlineKeyboardButton(
                    f"✅ Approve ${amount:.2f}", callback_data=f"approve_deposit_{deposit_id}"),
                InlineKeyboardButton(
                    f"❌ Deny ${amount:.2f}", callback_data=f"deny_deposit_{deposit_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🟡 <b>New Binance Deposit Claim</b>\n\n"
                    f"👤 <b>User:</b> {user.id} (@{user.username or 'Unknown'})\n"
                    f"💰 <b>Amount:</b> ${amount:.2f}\n"
                    f"🆔 <b>Deposit ID:</b> <code>{deposit_id}</code>\n"
                    f"💳 <b>Method:</b> Binance Transfer\n"
                    f"🆔 <b>Binance ID:</b> <code>{BINANCE_ID}</code>\n\n"
                    f"⚠️ <b>Action Required:</b> Verify Binance payment and approve/deny\n"
                    f"💡 <b>Note:</b> Check for transaction receipt or TXID from user"
                ),
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        except RuntimeError as e:
            logger.error("Failed to notify admin %s: %s", admin_id, e)

    await query.edit_message_text(
        f"✅ <b>Binance Deposit Claim Submitted</b>\n\n"
        f"🆔 <b>Deposit ID:</b> <code>{deposit_id}</code>\n\n"
        f"👨‍💼 Admins have been notified and will verify your Binance payment.\n"
        f"⏰ You'll be notified once the deposit is approved.\n\n"
        f"💡 <b>Note:</b> Please provide Transaction ID (TXID) or screenshot if requested by admin.",
        parse_mode='HTML'
    )

    logger.info("🟡 Binance deposit claim submitted by user %s: %s",
                user.id, deposit_id)


async def handle_cancel_deposit(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit cancellation"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    await query.edit_message_text(
        "❌ <b>Deposit Cancelled</b>\n\n"
        "You can start a new deposit anytime using /balance or the wallet menu.",
        parse_mode='HTML'
    )

    user_id = query.from_user.id if query.from_user else "Unknown"
    logger.info("💰 Deposit cancelled by user %s", user_id)


async def handle_transaction_history(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Show full transaction history"""
    if not update.callback_query:
        return

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    if not wallet_system:
        await query.edit_message_text("❌ Wallet system not available.")
        return

    # Get full transaction history
    transactions = wallet_system.get_transaction_history(user.id, limit=20)

    if not transactions:
        await query.edit_message_text(
            "📝 <b>Transaction History</b>\n\n"
            "No transactions found.\n\n"
            "💡 Add funds to start using the service!",
            parse_mode='HTML'
        )
        return

    # Format transaction history
    history_text = "📝 <b>Transaction History</b>\n\n"

    for tx in transactions:
        tx_type_emoji = {
            'deposit': '💰',
            'deduction': '💸',
            'refund': '💫',
            'admin_credit': '🎁'
        }
        emoji = tx_type_emoji.get(tx['transaction_type'], '📄')
        amount_sign = '+' if tx['transaction_type'] in ['deposit',
                                                        'refund', 'admin_credit'] else '-'

        # Format timestamp
        tx_time = datetime.fromisoformat(
            tx['timestamp']).strftime('%m/%d/%y %H:%M')

        history_text += (
            f"{emoji} <b>{amount_sign}${tx['amount']:.2f}</b>\n"
            f"   {tx['description']}\n"
            f"   <i>{tx_time} | Balance: ${tx['balance_after']:.2f}</i>\n\n"
        )

    # Add navigation buttons
    keyboard = [[
        InlineKeyboardButton("💰 Current Balance",
                             callback_data="show_balance"),
        InlineKeyboardButton("🔙 Back", callback_data="show_balance")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        history_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def handle_approve_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit approval by admin"""
    query = update.callback_query
    if not query or not query.from_user or not query.data:
        return

    # Extract deposit ID from callback data: "approve_deposit_DEP_123456789_1754854768"
    # Get "DEP_123456789_1754854768"
    deposit_id = "_".join(query.data.split('_')[2:])
    admin_id = query.from_user.id

    if not is_admin(admin_id):
        await query.answer("❌ Access denied.")
        return

    await query.answer()

    if not wallet_system:
        await query.edit_message_text("❌ Wallet system not available.")
        return

    # Approve the deposit
    success = wallet_system.approve_deposit(deposit_id, admin_id)

    if success:
        deposit = wallet_system.get_deposit_status(deposit_id)
        if not deposit:
            await query.edit_message_text("❌ Deposit not found.")
            return

        user_id = deposit['user_id']
        amount = deposit['amount_usd']

        # Admin notification
        await query.edit_message_text(
            f"✅ <b>Deposit Approved</b>\n\n"
            f"Deposit {deposit_id} has been approved.\n"
            f"User {user_id} wallet credited with ${amount:.2f}.",
            parse_mode='HTML'
        )

        # Notify user
        try:
            new_balance = wallet_system.get_user_balance(user_id)

            keyboard = [[
                InlineKeyboardButton("📱 Browse Services",
                                     callback_data="browse_services"),
                InlineKeyboardButton(
                    "💰 Check Balance", callback_data="show_balance")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ <b>Deposit Approved!</b>\n\n"
                    f"💰 <b>Amount:</b> ${amount:.2f}\n"
                    f"💰 <b>New Balance:</b> ${new_balance:.2f}\n\n"
                    f"🎉 Your wallet has been credited!\n"
                    f"You can now purchase SMS services instantly."
                ),
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        except RuntimeError as notify_error:
            logger.error("Failed to notify user %s: %s", user_id, notify_error)

        logger.info("✅ Deposit %s approved by admin %s", deposit_id, admin_id)

    else:
        await query.edit_message_text(
            f"❌ <b>Approval Failed</b>\n\n"
            f"Could not approve deposit {deposit_id}.\n"
            f"Deposit may have expired or already been processed.",
            parse_mode='HTML'
        )


async def handle_deny_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit denial by admin"""
    query = update.callback_query
    if not query or not query.from_user or not query.data:
        return

    # Extract deposit ID from callback data: "deny_deposit_DEP_123456789_1754854768"
    # Get "DEP_123456789_1754854768"
    deposit_id = "_".join(query.data.split('_')[2:])
    admin_id = query.from_user.id

    if not is_admin(admin_id):
        await query.answer("❌ Access denied.")
        return

    await query.answer()

    if not wallet_system:
        await query.edit_message_text("❌ Wallet system not available.")
        return

    deposit = wallet_system.get_deposit_status(deposit_id)
    if deposit:
        user_id = deposit['user_id']
        amount = deposit['amount_usd']

        # Update deposit status to denied
        if wallet_system and hasattr(wallet_system, 'deposits_table') and wallet_system.deposits_table:
            Deposit = Query()
            wallet_system.deposits_table.update({
                'status': 'denied',
                'admin_denied_at': datetime.now().isoformat(),
                'admin_denied_by': str(admin_id)
            }, Deposit.deposit_id == deposit_id)
        else:
            logger.warning(
                "⚠️ Cannot update deposit status - deposits_table not available")

        # Admin notification
        await query.edit_message_text(
            f"❌ <b>Deposit Denied</b>\n\n"
            f"Deposit {deposit_id} has been denied.\n"
            f"User {user_id} has been notified.",
            parse_mode='HTML'
        )

        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"❌ <b>Deposit Denied</b>\n\n"
                    f"💰 <b>Amount:</b> ${amount:.2f}\n"
                    f"🆔 <b>Deposit ID:</b> <code>{deposit_id}</code>\n\n"
                    f"Your deposit was not approved. Please ensure:\n"
                    f"• Exact amount was sent\n"
                    f"• Payment was sent to correct wallet\n"
                    f"• Transaction screenshot is clear\n\n"
                    f"Contact admin if you believe this is an error."
                ),
                parse_mode='HTML'
            )
        except RuntimeError as notify_error:
            logger.error("Failed to notify user %s: %s", user_id, notify_error)

        logger.info("❌ Deposit %s denied by admin %s", deposit_id, admin_id)

    else:
        await query.edit_message_text("❌ Deposit not found.")


# =============================================================================
# CALLBACK QUERY HANDLERS
# =============================================================================


async def handle_browse_services(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle service browsing - show available services with pricing"""
    if not update.callback_query:
        return

    query = update.callback_query
    await query.answer()

    # Show loading message
    await query.edit_message_text(
        "🔄 Loading services...",
        parse_mode='HTML'
    )

    try:
        if not sms_api:
            await query.edit_message_text(
                "❌ SMS API not initialized. Please contact administrator."
            )
            return

        # Get available services with pricing
        services_info = await sms_api.get_available_services_for_purchase()

        if not services_info.get('success') or not services_info.get('services'):
            keyboard = [
                [InlineKeyboardButton(
                    "🔄 Refresh Services", callback_data="browse_services")],
                [InlineKeyboardButton(
                    "🔙 Back to Menu", callback_data="start_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "❌ <b>No Services Available</b>\n\n"
                "Please try refreshing in a few moments.",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return

        # Build service selection menu (minimal design)
        services = services_info['services']
        message_text = "📱 <b>SMS Services</b>\n\n"

        keyboard = []
        for service in services:
            service_name = service['name']
            selling_price = service['selling_price']

            # Simple button with just name and price
            button_text = f"{'⭐ ' if service['recommended'] else ''}{service_name} - ${selling_price:.2f}"
            callback_data = f"select_service_{service['id']}_{selling_price}"
            keyboard.append([InlineKeyboardButton(
                button_text, callback_data=callback_data)])

        message_text += "Choose a service:"

        # Add refresh and back buttons
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh Availability",
                                 callback_data="browse_services"),
            InlineKeyboardButton(
                "🔙 Back to Menu", callback_data="start_menu")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        # Log service display for monitoring
        logger.info(
            "✅ Displayed %d available services to user %s", len(services), query.from_user.id if query.from_user else 'Unknown')

    except RuntimeError as e:
        logger.error("❌ Error browsing services: %s", str(e))
        keyboard = [
            [InlineKeyboardButton(
                "🔄 Try Again", callback_data="browse_services")],
            [InlineKeyboardButton(
                "🔙 Back to Menu", callback_data="start_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"❌ <b>Error Loading Services</b>\n\n"
            f"Please try again.",
            parse_mode='HTML',
            reply_markup=reply_markup
        )


async def handle_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle service selection - then show countries for that service"""
    if not update.callback_query:
        return

    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    try:
        # Extract service info from callback data: "select_service_1574_0.17"
        parts = query.data.split('_')
        if len(parts) < 4:
            raise ValueError("Invalid service callback data format")

        service_id = int(parts[2])
        selling_price = float(parts[3])

        # Store selected service in user data
        if context.user_data is not None:
            context.user_data['selected_service_id'] = service_id
            context.user_data['selected_price'] = selling_price

        # Show country selection for this service
        await query.edit_message_text(
            "🔄 <b>Loading Countries...</b>\n\n"
            "Checking country availability for your selected service...",
            parse_mode='HTML'
        )

        # Get service info
        service_name = "Unknown Service"
        try:
            from src.config import Config
            services = Config.SERVICE_PRIORITY
            service_info = next(
                (s for s in services if s['id'] == service_id), None)
            if service_info:
                service_name = service_info['name']
        except Exception:
            # Fallback service names
            service_names = {1574: 'Ring4', 22: 'Telegram',
                             395: 'Google', 1012: 'WhatsApp'}
            service_name = service_names.get(
                service_id, f'Service {service_id}')

        await load_countries_for_service(query, service_id, service_name, selling_price)

    except (ValueError, IndexError) as e:
        logger.error("❌ Error processing service selection: %s", e)
        await query.edit_message_text("❌ Invalid service selection. Please try again.")
    except Exception as e:
        logger.error("❌ Unexpected error in service selection: %s", e)
        await query.edit_message_text("❌ An error occurred. Please try again.")


async def load_countries_for_service(query, service_id: int, service_name: str, selling_price: float):
    """Load and display available countries for selected service"""
    if not sms_api:
        await query.edit_message_text("❌ SMS API not available.")
        return

    try:
        # Get popular countries first
        popular_countries = []
        try:
            from src.smspool_api import POPULAR_COUNTRIES
            # First 10 popular countries
            popular_countries = POPULAR_COUNTRIES[:10]
        except ImportError:
            # Fallback to hardcoded popular countries
            popular_countries = [
                {"id": 1, "name": "United States", "code": "US", "flag": "🇺🇸"},
                {"id": 2, "name": "United Kingdom", "code": "GB", "flag": "🇬🇧"},
                {"id": 3, "name": "Canada", "code": "CA", "flag": "🇨🇦"},
                {"id": 7, "name": "France", "code": "FR", "flag": "🇫🇷"},
                {"id": 9, "name": "Germany", "code": "DE", "flag": "🇩🇪"},
            ]

        keyboard = []

        # Add search functionality
        keyboard.append([
            InlineKeyboardButton("🔍 Search Countries",
                                 callback_data=f"search_countries_{service_id}")
        ])

        service_text = f"🌍 <b>Select Country for {service_name}</b>\n\n"
        service_text += f"💰 <b>Price:</b> ${selling_price:.2f}\n"
        service_text += f"📱 <b>Service:</b> {service_name}\n\n"
        service_text += "Choose your country (popular countries shown first):\n\n"

        # Check availability for each popular country
        available_countries = []
        for country in popular_countries:
            try:
                # Quick availability check
                availability = await sms_api.check_service_availability(service_id, country['id'])
                if availability.get('available'):
                    available_countries.append(country)
                    if len(available_countries) >= 8:  # Limit to 8 countries for UI
                        break
            except Exception as check_error:
                logger.warning(
                    f"Failed to check availability for {country['name']}: {check_error}")
                continue

        if not available_countries:
            await query.edit_message_text(
                f"❌ <b>Service Not Available</b>\n\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"💰 <b>Price:</b> ${selling_price:.2f}\n\n"
                f"Unfortunately, {service_name} is not available in any supported countries at the moment.\n"
                f"Please try a different service or check back later.",
                parse_mode='HTML'
            )
            return

        service_text += f"✅ <b>Available in {len(available_countries)} countries:</b>\n\n"

        # Show available countries in rows of 2
        for i in range(0, len(available_countries), 2):
            row = []
            for j in range(2):
                if i + j < len(available_countries):
                    country = available_countries[i + j]
                    row.append(InlineKeyboardButton(
                        f"{country['flag']} {country['name']}",
                        callback_data=f"country_{country['id']}_{service_id}_{selling_price:.2f}"
                    ))
            keyboard.append(row)

        # Add "Show All Countries" button
        keyboard.append([
            InlineKeyboardButton(
                "🌐 Show All Countries", callback_data=f"all_countries_{service_id}_{selling_price:.2f}")
        ])

        # Add back button
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Services",
                                 callback_data="browse_services")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            service_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        logger.info("✅ Loaded %d countries for service %s",
                    len(available_countries), service_name)

    except Exception as e:
        logger.error("❌ Error loading countries for %s: %s", service_name, e)
        await query.edit_message_text(
            f"❌ <b>Error Loading Countries</b>\n\n"
            f"Unable to load countries for {service_name}. Please try again.",
            parse_mode='HTML'
        )


async def handle_country_selection_with_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country selection for a specific service"""
    if not update.callback_query:
        return

    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    try:
        # Extract info from callback data: "country_1_1574_0.17"
        parts = query.data.split('_')
        if len(parts) < 4:
            raise ValueError("Invalid country callback data format")

        country_id = int(parts[1])
        service_id = int(parts[2])
        selling_price = float(parts[3])

        # Store selections in user data
        if context.user_data is not None:
            context.user_data['selected_country_id'] = country_id
            context.user_data['selected_service_id'] = service_id
            context.user_data['selected_price'] = selling_price

        # Get country and service info
        country = sms_api.get_country_by_id(country_id) if sms_api else None
        if not country:
            await query.edit_message_text("❌ Invalid country selection. Please try again.")
            return

        country_name = country.get("name", "Unknown") if country else "Unknown"
        country_flag = country.get("flag", "🌍") if country else "🌍"

        # Get service name
        service_name = "Unknown Service"
        if sms_api:
            try:
                from src.config import Config
                services = Config.SERVICE_PRIORITY
                service_info = next(
                    (s for s in services if s['id'] == service_id), None)
                if service_info:
                    service_name = service_info['name']
            except Exception:
                # Fallback service names
                service_names = {1574: 'Ring4', 22: 'Telegram',
                                 395: 'Google', 1012: 'WhatsApp'}
                service_name = service_names.get(
                    service_id, f'Service {service_id}')

        # Check availability for this specific service and country combination
        await query.edit_message_text(
            f"🔍 <b>Checking Availability</b>\n\n"
            f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
            f"📱 <b>Service:</b> {service_name}\n"
            f"💰 <b>Price:</b> ${selling_price:.2f}\n\n"
            "⏳ Verifying service availability in your selected country...",
            parse_mode='HTML'
        )

        # Check service availability for this country
        if not sms_api:
            await query.edit_message_text("❌ SMS API not available.")
            return

        availability = await sms_api.check_service_availability(service_id, country_id)

        if not availability.get('available'):
            # Service not available in this country
            keyboard = [[
                InlineKeyboardButton("🔙 Choose Different Country",
                                     callback_data=f"select_service_{service_id}_{selling_price:.2f}"),
                InlineKeyboardButton("🔄 Try Different Service",
                                     callback_data="browse_services")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"❌ <b>Service Not Available</b>\n\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"📱 <b>Service:</b> {service_name}\n\n"
                f"Unfortunately, {service_name} is not available in {country_name}.\n"
                f"Please try a different country or service.",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return

        # Service is available! Show purchase confirmation
        user = query.from_user
        if not user:
            return

        user_balance = wallet_system.get_user_balance(
            user.id) if wallet_system else 0.00

        # Check if user has sufficient balance
        if user_balance < selling_price:
            keyboard = [[
                InlineKeyboardButton(
                    "💰 Add Funds", callback_data="deposit_funds"),
                InlineKeyboardButton("🔙 Back to Services",
                                     callback_data="browse_services")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"❌ <b>Insufficient Balance</b>\n\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"💰 <b>Price:</b> ${selling_price:.2f}\n"
                f"💰 <b>Your Balance:</b> ${user_balance:.2f}\n"
                f"📉 <b>Need:</b> ${selling_price - user_balance:.2f} more\n\n"
                f"Please add funds to your wallet to continue.",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return

        # User has sufficient balance - show instant purchase option
        keyboard = [[
            InlineKeyboardButton(f"⚡ Buy Now (${selling_price:.2f})",
                                 callback_data=f"instant_purchase_{service_id}_{country_id}_{selling_price:.2f}"),
        ], [
            InlineKeyboardButton("🔙 Back to Countries",
                                 callback_data=f"select_service_{service_id}_{selling_price:.2f}"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="start")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ <b>Ready to Purchase!</b>\n\n"
            f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
            f"📱 <b>Service:</b> {service_name}\n"
            f"💰 <b>Price:</b> ${selling_price:.2f}\n"
            f"💰 <b>Your Balance:</b> ${user_balance:.2f}\n"
            f"💰 <b>After Purchase:</b> ${user_balance - selling_price:.2f}\n\n"
            f"🎯 <b>Service Available!</b> Click below to purchase instantly.\n"
            f"📲 You'll receive the phone number immediately.",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    except (ValueError, IndexError) as e:
        logger.error("❌ Error processing country selection: %s", e)
        await query.edit_message_text("❌ Invalid country selection. Please try again.")
    except Exception as e:
        logger.error("❌ Unexpected error in country selection: %s", e)
        await query.edit_message_text("❌ An error occurred. Please try again.")


async def handle_instant_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle instant purchase after service and country selection"""
    if not update.callback_query:
        return

    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    try:
        # Extract info from callback data: "instant_purchase_1574_1_0.17"
        parts = query.data.split('_')
        if len(parts) < 4:
            raise ValueError("Invalid purchase callback data format")

        service_id = int(parts[2])
        country_id = int(parts[3])
        selling_price = float(parts[4])

        user = query.from_user
        if not user:
            return

        # Get service and country info for display
        service_name = "Unknown Service"
        country_name = "Unknown Country"
        country_flag = "🌍"

        if sms_api:
            try:
                from src.config import Config
                services = Config.SERVICE_PRIORITY
                service_info = next(
                    (s for s in services if s['id'] == service_id), None)
                if service_info:
                    service_name = service_info['name']
            except Exception:
                # Fallback service names
                service_names = {1574: 'Ring4', 22: 'Telegram',
                                 395: 'Google', 1012: 'WhatsApp'}
                service_name = service_names.get(
                    service_id, f'Service {service_id}')

            country = sms_api.get_country_by_id(country_id)
            if country:
                country_name = country.get("name", "Unknown")
                country_flag = country.get("flag", "🌍")

        # Show processing message
        await query.edit_message_text(
            f"⚡ <b>Processing Purchase...</b>\n\n"
            f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
            f"📱 <b>Service:</b> {service_name}\n"
            f"💰 <b>Price:</b> ${selling_price:.2f}\n\n"
            f"🔄 <b>Processing instant purchase...</b>\n"
            f"📱 Service will be delivered automatically",
            parse_mode='HTML'
        )

        # Process the wallet purchase with country info
        await process_wallet_service_purchase_with_country(
            user_id=user.id,
            context=context,
            send_method=query.edit_message_text,
            service_id=service_id,
            service_name=service_name,
            country_id=country_id,
            country_name=country_name,
            country_flag=country_flag
        )

    except (ValueError, IndexError) as e:
        logger.error("❌ Error processing instant purchase: %s", e)
        await query.edit_message_text("❌ Invalid purchase request. Please try again.")
    except Exception as e:
        logger.error("❌ Unexpected error in instant purchase: %s", e)
        await query.edit_message_text("❌ An error occurred during purchase. Please try again.")


async def handle_show_all_countries_for_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all countries for a specific service"""
    if not update.callback_query:
        return

    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    try:
        # Extract service info from callback data: "all_countries_1574_0.17"
        parts = query.data.split('_')
        if len(parts) < 4:
            raise ValueError("Invalid callback data format")

        service_id = int(parts[2])
        selling_price = float(parts[3])

        # Get service name
        service_name = "Unknown Service"
        try:
            from src.config import Config
            services = Config.SERVICE_PRIORITY
            service_info = next(
                (s for s in services if s['id'] == service_id), None)
            if service_info:
                service_name = service_info['name']
        except Exception:
            service_names = {1574: 'Ring4', 22: 'Telegram',
                             395: 'Google', 1012: 'WhatsApp'}
            service_name = service_names.get(
                service_id, f'Service {service_id}')

        await query.edit_message_text(
            f"🔄 <b>Loading All Countries for {service_name}...</b>\n\n"
            f"Checking availability in all supported countries...",
            parse_mode='HTML'
        )

        if not sms_api:
            await query.edit_message_text("❌ SMS API not available.")
            return

        # Get all countries from API
        try:
            from src.smspool_api import ALL_COUNTRIES
            all_countries = ALL_COUNTRIES[:30]  # Limit to first 30 for UI
        except ImportError:
            await query.edit_message_text("❌ Country data not available.")
            return

        # Check availability for all countries (limit checks for performance)
        available_countries = []
        for country in all_countries[:20]:  # Check first 20 countries only
            try:
                availability = await sms_api.check_service_availability(service_id, country['id'])
                if availability.get('available'):
                    available_countries.append(country)
                    if len(available_countries) >= 15:  # Limit results
                        break
            except Exception:
                continue

        if not available_countries:
            keyboard = [[
                InlineKeyboardButton("🔙 Back to Service",
                                     callback_data=f"select_service_{service_id}_{selling_price:.2f}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"❌ <b>No Countries Available</b>\n\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"💰 <b>Price:</b> ${selling_price:.2f}\n\n"
                f"Unfortunately, {service_name} is not available in any countries at the moment.",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return

        # Build country selection keyboard
        keyboard = []

        # Add search button
        keyboard.append([
            InlineKeyboardButton("🔍 Search Countries",
                                 callback_data=f"search_countries_{service_id}")
        ])

        # Show countries in rows of 2
        for i in range(0, len(available_countries), 2):
            row = []
            for j in range(2):
                if i + j < len(available_countries):
                    country = available_countries[i + j]
                    row.append(InlineKeyboardButton(
                        f"{country['flag']} {country['name']}",
                        callback_data=f"country_{country['id']}_{service_id}_{selling_price:.2f}"
                    ))
            keyboard.append(row)

        # Add back button
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Service",
                                 callback_data=f"select_service_{service_id}_{selling_price:.2f}")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        service_text = f"🌐 <b>All Countries for {service_name}</b>\n\n"
        service_text += f"💰 <b>Price:</b> ${selling_price:.2f}\n"
        service_text += f"📱 <b>Service:</b> {service_name}\n\n"
        service_text += f"✅ Available in {len(available_countries)} countries:\n"
        service_text += f"(Showing first {len(available_countries)} results)"

        await query.edit_message_text(
            service_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    except (ValueError, IndexError) as e:
        logger.error("❌ Error showing all countries: %s", e)
        await query.edit_message_text("❌ Invalid request. Please try again.")
    except Exception as e:
        logger.error("❌ Unexpected error showing all countries: %s", e)
        await query.edit_message_text("❌ An error occurred. Please try again.")


async def handle_country_search_for_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country search for a specific service"""
    if not update.callback_query:
        return

    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    try:
        # Extract service info from callback data: "search_countries_1574"
        parts = query.data.split('_')
        if len(parts) < 3:
            raise ValueError("Invalid callback data format")

        service_id = int(parts[2])

        # Get service name
        service_name = "Unknown Service"
        try:
            from src.config import Config
            services = Config.SERVICE_PRIORITY
            service_info = next(
                (s for s in services if s['id'] == service_id), None)
            if service_info:
                service_name = service_info['name']
        except Exception:
            service_names = {1574: 'Ring4', 22: 'Telegram',
                             395: 'Google', 1012: 'WhatsApp'}
            service_name = service_names.get(
                service_id, f'Service {service_id}')

        # Ask user to send country search query
        search_text = (
            f"🔍 <b>Search Countries for {service_name}</b>\n\n"
            f"💡 Send me the name or code of the country you're looking for.\n\n"
            f"<b>Examples:</b>\n"
            f"• United States\n"
            f"• UK\n"
            f"• Germany\n"
            f"• FR\n\n"
            f"❌ Send /cancel to go back"
        )

        keyboard = [[
            InlineKeyboardButton(
                "❌ Cancel", callback_data=f"select_service_{service_id}_0.17")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            search_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        # Set user state to expect country search for this service
        if context.user_data is not None:
            context.user_data['awaiting_country_search'] = True
            context.user_data['search_service_id'] = service_id

        logger.info("🔍 User %s requested country search for service %s",
                    query.from_user.id if query.from_user else 'Unknown', service_name)

    except (ValueError, IndexError) as e:
        logger.error("❌ Error setting up country search: %s", e)
        await query.edit_message_text("❌ Invalid request. Please try again.")
    except Exception as e:
        logger.error("❌ Unexpected error in country search setup: %s", e)
        await query.edit_message_text("❌ An error occurred. Please try again.")


def get_country_selection_keyboard(search_query: Optional[str] = None):
    """Create country selection keyboard"""
    if not sms_api:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ API Not Available", callback_data="error")
        ]])

    # Get countries based on search query
    if search_query:
        countries = sms_api.search_countries(search_query)
        title_text = f"🔍 Search results for '{search_query}'"
    else:
        countries = sms_api.get_countries_list() if sms_api else []
        title_text = "🌟 Popular Countries"

    keyboard = []

    # Add search button at the top
    keyboard.append([
        InlineKeyboardButton("🔍 Search Countries",
                             callback_data="search_countries")
    ])

    # Show countries in rows of 2
    for i in range(0, len(countries), 2):
        row = []
        for j in range(2):
            if i + j < len(countries):
                country = countries[i + j]
                button_text = f"{country['flag']} {country['name']}"
                callback_data = f"country_{country['id']}"
                row.append(InlineKeyboardButton(
                    button_text, callback_data=callback_data))
        keyboard.append(row)

    # Add "Show All Countries" if we're showing popular only
    if not search_query:
        keyboard.append([
            InlineKeyboardButton("🌐 Show All Countries",
                                 callback_data="all_countries")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🌟 Back to Popular",
                                 callback_data="browse_services")
        ])

    # Add back button
    keyboard.append([
        InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


async def handle_country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country selection from the country list"""
    if not update.callback_query:
        return

    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    try:
        # Extract country ID from callback data: "country_1"
        country_id = int(query.data.split('_')[1])

        # Store selected country in user data
        if context.user_data is not None:
            context.user_data['selected_country_id'] = country_id

        # Get country info
        country = sms_api.get_country_by_id(country_id) if sms_api else None
        if not country:
            await query.edit_message_text("❌ Invalid country selection. Please try again.")
            return

        country_name = country.get("name", "Unknown") if country else "Unknown"
        country_flag = country.get("flag", "🌍") if country else "🌍"

        # Show loading message
        await query.edit_message_text(
            f"🔄 <b>Loading Services for {country_flag} {country_name}...</b>\n\n"
            "Checking real-time pricing and availability...",
            parse_mode='HTML'
        )

        # Get available services for this country
        await load_services_for_country(query, country_id, country_name, country_flag)

    except (ValueError, IndexError) as e:
        logger.error(f"❌ Error processing country selection: {e}")
        await query.edit_message_text("❌ Invalid country selection. Please try again.")
    except Exception as e:
        logger.error(f"❌ Unexpected error in country selection: {e}")
        await query.edit_message_text("❌ Error loading country services. Please try again.")


async def load_services_for_country(query, country_id: int, country_name: str, country_flag: str):
    """Load and display available services for selected country"""
    if not sms_api:
        await query.edit_message_text("❌ SMS API not available.")
        return

    try:
        # Get available services for this country
        services_result = await sms_api.get_available_services_for_purchase(country_id)

        if not services_result.get('success', False):
            await query.edit_message_text(
                f"❌ Error loading services for {country_flag} {country_name}",
                parse_mode='HTML'
            )
            return

        services = services_result.get('services', [])

        if not services:
            # No services available for this country
            keyboard = [[
                InlineKeyboardButton(
                    "🔙 Choose Different Country", callback_data="browse_services")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"❌ No services for {country_flag} {country_name}",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return

        # Services available - create service selection keyboard
        keyboard = []

        # Add title row
        service_text = f"📱 <b>{country_flag} {country_name}</b>\n\n"

        # Add each service as a button
        for service in services:
            service_name = service['name']
            selling_price = service['selling_price']
            recommended = service.get('recommended', False)

            button_text = f"{'⭐ ' if recommended else ''}{service_name} - ${selling_price:.2f}"
            callback_data = f"service_{service['id']}_{country_id}_{selling_price}"

            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=callback_data)
            ])

        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("🔙 Choose Different Country",
                                 callback_data="browse_services"),
            InlineKeyboardButton(
                "💰 Check Balance", callback_data="show_balance")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            service_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        logger.info(f"✅ Loaded {len(services)} services for {country_name}")

    except Exception as e:
        logger.error(f"❌ Error loading services for {country_name}: {e}")
        await query.edit_message_text(
            f"❌ Error loading services for {country_flag} {country_name}",
            f"Error: {str(e)}\n\n"
            "Please try again later.",
            parse_mode='HTML'
        )


async def handle_show_all_countries(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Show all countries instead of just popular ones"""
    if not update.callback_query:
        return

    query = update.callback_query
    await query.answer()

    if not sms_api:
        await query.edit_message_text("❌ SMS API not available.")
        return

    # Get all countries
    countries = sms_api.get_countries_list() if sms_api else []

    keyboard = []

    # Add search button at the top
    keyboard.append([
        InlineKeyboardButton("🔍 Search Countries",
                             callback_data="search_countries")
    ])

    # Show countries in rows of 2 (limit to first 20 to avoid message too long)
    display_countries = countries[:40]  # Show first 40 countries

    for i in range(0, len(display_countries), 2):
        row = []
        for j in range(2):
            if i + j < len(display_countries):
                country = display_countries[i + j]
                button_text = f"{country['flag']} {country['name']}"
                callback_data = f"country_{country['id']}"
                row.append(InlineKeyboardButton(
                    button_text, callback_data=callback_data))
        keyboard.append(row)

    # Add navigation buttons
    keyboard.append([
        InlineKeyboardButton("🌟 Show Popular Only",
                             callback_data="browse_services"),
        InlineKeyboardButton("🔙 Back to Menu", callback_data="start_menu")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"🌐 <b>All Countries</b>\n\n"
        f"Showing {len(display_countries)} countries (more available via search).\n"
        f"Use search to find specific countries quickly.",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def handle_country_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country search request"""
    if not update.callback_query:
        return

    query = update.callback_query
    await query.answer()

    # Ask user to send country search query
    search_text = (
        f"🔍 <b>Search Countries</b>\n\n"
        f"💡 Send me the name or code of the country you're looking for.\n\n"
        f"<b>Examples:</b>\n"
        f"• United States\n"
        f"• UK\n"
        f"• Germany\n"
        f"• FR\n\n"
        f"❌ Send /cancel to go back"
    )

    keyboard = [[
        InlineKeyboardButton("❌ Cancel", callback_data="browse_services")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        search_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

    # Set user state to expect country search
    if context.user_data is not None:
        context.user_data['awaiting_country_search'] = True
    logger.info("🔍 User %s requested country search",
                query.from_user.id if query.from_user else 'Unknown')


async def handle_service_selection_with_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle service selection with country information"""
    if not update.callback_query:
        return

    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    try:
        # Extract service info from callback data: "service_1574_1_0.17"
        parts = query.data.split('_')
        if len(parts) < 4:
            raise ValueError("Invalid service callback data format")

        service_id = int(parts[1])
        country_id = int(parts[2])
        selling_price = float(parts[3])

        # Get service and country info
        if not sms_api:
            await query.edit_message_text("❌ SMS API not available.")
            return

        country = sms_api.get_country_by_id(country_id)
        if not country:
            await query.edit_message_text("❌ Invalid country selection.")
            return

        country_name = country["name"]
        country_flag = country["flag"]

        # Get service name from known services
        service_names = {1574: 'Ring4', 22: 'Telegram',
                         395: 'Google', 1012: 'WhatsApp'}
        service_name = service_names.get(service_id, f'Service {service_id}')

        # Store selection in user data
        if context.user_data is not None:
            context.user_data.update({
                'selected_service_id': service_id,
                'selected_service_name': service_name,
                'selected_country_id': country_id,
                'selected_price': selling_price
            })

        # Check user balance and proceed with purchase
        await handle_service_purchase_with_country(query, context, service_id, service_name, country_id, country_name, country_flag, selling_price)

    except (ValueError, IndexError) as e:
        logger.error(f"❌ Error processing service selection: {e}")
        await query.edit_message_text("❌ Invalid service selection. Please try again.")
    except Exception as e:
        logger.error(f"❌ Unexpected error in service selection: {e}")
        await query.edit_message_text("❌ Error processing service selection. Please try again.")


async def handle_service_purchase_with_country(query, context: ContextTypes.DEFAULT_TYPE, service_id: int, service_name: str, country_id: int, country_name: str, country_flag: str, selling_price: float):
    """Handle service purchase with country information"""
    user = query.from_user
    if not user:
        await query.edit_message_text("❌ User information not available.")
        return

    user_logger.info(
        "🛒 User %s (@%s) initiating %s purchase in %s - $%.2f",
        user.id, user.username, service_name, country_name, selling_price)

    # Step 1: Check availability for this specific country and service
    await query.edit_message_text(
        f"🔍 <b>Checking {service_name} Availability</b>\n\n"
        f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
        f"📱 <b>Service:</b> {service_name}\n"
        f"💰 <b>Price:</b> ${selling_price:.2f}\n\n"
        "⏳ Real-time availability check in progress...",
        parse_mode='HTML'
    )

    if not sms_api:
        await query.edit_message_text("❌ SMS API not available.")
        return

    try:
        # Check service availability for this country
        availability = await sms_api.check_service_availability(service_id, country_id)

        if not availability.get('available'):
            # Service not available in this country
            keyboard = [[
                InlineKeyboardButton(
                    "🔙 Choose Different Service", callback_data=f"country_{country_id}"),
                InlineKeyboardButton(
                    "🌍 Choose Different Country", callback_data="browse_services")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"❌ <b>Service Unavailable</b>\n\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"📱 <b>Service:</b> {service_name}\n\n"
                f"😔 {availability.get('message', 'Service not available')}\n\n"
                f"💡 <b>Options:</b>\n"
                f"• Try a different service for {country_name}\n"
                f"• Choose a different country\n"
                f"• Check back later",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return

        # Step 2: Check wallet balance
        user_balance = wallet_system.get_user_balance(
            user.id) if wallet_system else 0.00

        await query.edit_message_text(
            f"✅ <b>{service_name} Available!</b>\n\n"
            f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
            f"📱 <b>Service:</b> {service_name}\n"
            f"💰 <b>Service Price:</b> ${selling_price:.2f}\n"
            f"💰 <b>Your Balance:</b> ${user_balance:.2f}\n\n"
            "⚡ Checking wallet balance...",
            parse_mode='HTML'
        )

        # Step 3: Wallet balance check
        if not wallet_system:
            await query.edit_message_text("❌ Wallet system not available.")
            return

        if not wallet_system.has_sufficient_balance(user.id, selling_price):
            # Insufficient balance
            keyboard = [[
                InlineKeyboardButton(
                    "💰 Add Funds", callback_data="deposit_funds"),
                InlineKeyboardButton(
                    "🔙 Back", callback_data=f"country_{country_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"💰 <b>Insufficient Balance</b>\n\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"💰 <b>Required:</b> ${selling_price:.2f}\n"
                f"💰 <b>Your Balance:</b> ${user_balance:.2f}\n"
                f"💸 <b>Needed:</b> ${selling_price - user_balance:.2f}\n\n"
                f"💡 Add funds to your wallet to continue.",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return

        # User has sufficient balance - proceed with instant purchase
        user_logger.info(
            "⚡ Instant purchase: User %s has sufficient balance ($%.2f) for %s in %s",
            user.id, user_balance, service_name, country_name)

        # AUTO-PROCESS purchase immediately without confirmation
        await query.edit_message_text(
            f"⚡ <b>Processing Purchase...</b>\n\n"
            f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
            f"📱 <b>Service:</b> {service_name}\n"
            f"💰 <b>Cost:</b> ${selling_price:.2f}\n"
            f"💰 <b>Your Balance:</b> ${user_balance:.2f}\n"
            f"💰 <b>After Purchase:</b> ${user_balance - selling_price:.2f}\n\n"
            f"🔄 <b>Processing instant purchase...</b>\n"
            f"📞 Service will be delivered automatically",
            parse_mode='HTML'
        )

        # Process the wallet purchase immediately
        await process_wallet_service_purchase_with_country(
            user_id=user.id,
            context=context,
            send_method=query.edit_message_text,
            service_id=service_id,
            service_name=service_name,
            country_id=country_id,
            country_name=country_name,
            country_flag=country_flag
        )

    except Exception as e:
        logger.error(f"❌ Error in service purchase for {country_name}: {e}")
        await query.edit_message_text(
            f"❌ <b>Purchase Error</b>\n\n"
            f"Error processing {service_name} purchase for {country_flag} {country_name}.\n\n"
            f"Please try again later or contact support.",
            parse_mode='HTML'
        )


async def process_wallet_service_purchase_with_country(user_id: int, context: ContextTypes.DEFAULT_TYPE, send_method, service_id: int, service_name: str, country_id: int, country_name: str, country_flag: str):
    """Process service purchase using wallet balance with country support"""

    # Get the selected price from user data
    selling_price = context.user_data.get(
        'selected_price', 0.15) if context.user_data else 0.15

    purchase_logger.info(
        "🚀 Starting wallet purchase for user %s: %s in %s ($%.2f)", user_id, service_name, country_name, selling_price)

    start_time = asyncio.get_event_loop().time()
    order_id = None

    try:
        # Step 1: Deduct from wallet first
        if not wallet_system:
            await send_method(
                "❌ <b>Wallet system not available</b>\n\n"
                "Please contact support.",
                parse_mode='HTML'
            )
            return

        deduction_success = wallet_system.deduct_balance(
            user_id, selling_price, f"{service_name} purchase for {country_name}")

        if not deduction_success:
            await send_method(
                f"❌ <b>Payment Failed</b>\n\n"
                f"Could not deduct ${selling_price:.2f} from wallet.\n"
                f"Please check your balance and try again.",
                parse_mode='HTML'
            )
            return

        performance_logger.info(
            "✅ Wallet deducted: $%.2f for user %s", selling_price, user_id)

        # Step 2: Purchase from SMS API
        await send_method(
            f"💰 <b>Payment Processed</b>\n\n"
            f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
            f"📱 <b>Service:</b> {service_name}\n"
            f"💰 <b>Charged:</b> ${selling_price:.2f}\n\n"
            f"📞 <b>Purchasing phone number...</b>\n"
            f"⏳ This usually takes 5-10 seconds",
            parse_mode='HTML'
        )

        # Use the new country-aware purchase method
        if not sms_api:
            # Refund the user since API is not available
            if wallet_system:
                wallet_system.add_balance(
                    user_id, selling_price, f"Refund for {service_name} - API unavailable")
            await send_method(
                "❌ <b>Service Unavailable</b>\n\n"
                "SMS service is currently unavailable. Your payment has been refunded.",
                parse_mode='HTML'
            )
            return

        purchase_result = await sms_api.purchase_specific_service(service_id, service_name, country_id)

        if purchase_result.get('success'):
            # Success - create order and start OTP polling
            order_data = {
                'order_id': purchase_result['order_id'],
                'number': purchase_result['number'],
                'cost': selling_price,  # Use our selling price
                'service_id': service_id,  # Required for instant refund
                'service_name': service_name,
                'country_id': country_id,
                'country_name': country_name,
                'country_flag': country_flag,
                'actual_cost': purchase_result.get('cost', selling_price)
            }

            # Create order in database
            db.create_order(user_id, order_data)
            order_id = purchase_result['order_id']

            # Show success message with number
            success_text = (
                f"✅ <b>{service_name} Number Purchased!</b>\n\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"📞 <b>Phone Number:</b> <code>{purchase_result['number']}</code>\n"
                f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
                f"💰 <b>Cost:</b> ${selling_price:.2f}\n\n"
                f"🔄 <b>Waiting for SMS...</b>\n"
                f"⏰ Valid for {POLL_TIMEOUT // 60} minutes\n"
                f"📱 Use this number for verification now!\n\n"
                f"💡 Your OTP code will appear here automatically."
            )

            # Add instant refund and get different number buttons
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 Get Different Number", callback_data=f"instant_refund_reorder_{order_id}"),
                ],
                [
                    InlineKeyboardButton(
                        "💰 Instant Refund", callback_data=f"refund_{order_id}"),
                    InlineKeyboardButton(
                        "❌ Cancel Order", callback_data=f"cancel_order_{order_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await send_method(success_text, parse_mode='HTML', reply_markup=reply_markup)

            # Start OTP polling
            start_otp_polling(order_id, user_id, context)

            end_time = asyncio.get_event_loop().time()
            performance_logger.info(
                "✅ Purchase completed in %.2f seconds for %s in %s",
                end_time - start_time, service_name, country_name)

        else:
            # Purchase failed - refund to wallet
            refund_success = wallet_system.add_balance(
                user_id, selling_price, f"Refund for failed {service_name} purchase in {country_name}")

            error_msg = purchase_result.get('message', 'Unknown error')
            await send_method(
                f"❌ <b>Purchase Failed</b>\n\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"⚠️ <b>Error:</b> {error_msg}\n\n"
                f"💰 <b>Refund:</b> {'✅ Processed' if refund_success else '❌ Failed'}\n"
                f"${selling_price:.2f} {'returned to wallet' if refund_success else 'refund failed'}\n\n"
                f"💡 Try a different service or country.",
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(
            f"❌ Critical error in wallet purchase for {country_name}: {e}")

        # Attempt refund on error
        if selling_price > 0 and wallet_system:
            refund_success = wallet_system.add_balance(
                user_id, selling_price, f"Error refund for {service_name} in {country_name}")

            await send_method(
                f"❌ <b>Purchase Error</b>\n\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"⚠️ <b>Error:</b> {str(e)}\n\n"
                f"💰 <b>Refund:</b> {'✅ Processed' if refund_success else '❌ Failed'}\n"
                f"${selling_price:.2f} {'returned to wallet' if refund_success else 'refund failed'}\n\n"
                f"💡 Please try again or contact support.",
                parse_mode='HTML'
            )

    finally:
        performance_logger.info(
            "🧹 Purchase cleanup completed for %s in %s", service_name, country_name)


async def handle_service_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, service_id: int, service_name: str, selling_price: float):
    """Optimized purchase flow with real-time availability checking"""
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        logger.error("❌ Missing query or user in service purchase")
        return

    user_logger.info(
        "🛒 User %s (@%s) initiating %s purchase - $%.2f", user.id, user.username, service_name, selling_price)
    performance_logger.info(
        "⏱️ Starting purchase flow for service %s", service_id)

    # Step 1: Immediate availability check with optimized async
    await query.edit_message_text(
        f"🔍 <b>Checking {service_name} Availability...</b>\n\n"
        f"💰 <b>Price:</b> ${selling_price}\n"
        f"📱 <b>Service:</b> {service_name}\n\n"
        "⏳ Real-time availability check in progress...",
        parse_mode='HTML'
    )

    if not sms_api:
        logger.error("❌ SMS API not initialized - critical system error")
        await query.edit_message_text("❌ SMS API not initialized.")
        return

    # Optimized concurrent availability and balance checks
    try:
        performance_logger.debug(
            "🔍 Starting concurrent availability checks for %s", service_name)

        # Run availability check and balance check concurrently for speed
        # Default to country_id=1 (USA) for availability check
        availability_task = asyncio.create_task(
            sms_api.check_service_availability(service_id, 1)
        )
        balance_task = asyncio.create_task(sms_api.check_balance())

        # Wait for both checks to complete
        availability_result, balance_result = await asyncio.gather(
            availability_task, balance_task, return_exceptions=True
        )

        performance_logger.info(
            "⚡ Concurrent checks completed for %s", service_name)

        # Process availability result
        if isinstance(availability_result, Exception):
            logger.error("❌ Availability check failed: %s",
                         str(availability_result))
            await query.edit_message_text(
                f"❌ <b>Service Check Failed</b>\n\n"
                f"Unable to verify {service_name} availability.\n"
                f"Please try again later.",
                parse_mode='HTML'
            )
            return

        # At this point, availability_result is a dict, not an exception
        if not isinstance(availability_result, dict) or not availability_result.get('available', False):
            error_msg = availability_result.get(
                'message', f'{service_name} service temporarily unavailable') if isinstance(availability_result, dict) else f'{service_name} service temporarily unavailable'
            user_logger.warning(
                "⚠️ %s unavailable for user %s: %s", service_name, user.id, error_msg)

            await query.edit_message_text(
                f"❌ <b>{service_name} Unavailable</b>\n\n"
                f"💰 <b>Price:</b> ${selling_price}\n"
                f"📱 <b>Service:</b> {service_name}\n\n"
                f"⚠️ <b>Issue:</b> {error_msg}\n\n"
                "💡 <b>Tip:</b> Try another service or check back in a few minutes.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🔙 Back to Services", callback_data="browse_services")
                ]])
            )
            return

        # Process balance result (if not exception)
        if not isinstance(balance_result, Exception) and isinstance(balance_result, dict) and balance_result.get('success'):
            current_balance = float(balance_result.get('balance', '0.0'))
            api_logger.debug("💰 Current API balance: $%.2f", current_balance)

            # Estimate required balance (API price + buffer)
            estimated_api_cost = selling_price * 0.8  # Rough estimate
            if current_balance < estimated_api_cost:
                api_logger.warning(
                    "⚠️ Low API balance: $%.2f < $%.2f", current_balance, estimated_api_cost)

    except RuntimeError as e:
        logger.error(
            "❌ Error during availability checks for %s: %s", service_name, str(e))
        performance_logger.error(
            "⚠️ Availability check failed for service %s: %s", service_id, e)
        await query.edit_message_text(
            f"❌ <b>Service Check Failed</b>\n\n"
            f"Unable to verify {service_name} availability.\n"
            "🔧 <b>Error:</b> {str(e)[:100]}...\n\n"
            "Please try again in a moment.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Services",
                                     callback_data="browse_services")
            ]])
        )
        return

    # Step 2: Service confirmed available - proceed with wallet-based purchase
    user_logger.info(
        "✅ %s confirmed available for user %s", service_name, user.id)

    # Get user's wallet balance
    user_balance = wallet_system.get_user_balance(
        user.id) if wallet_system else 0.00

    await query.edit_message_text(
        f"✅ <b>{service_name} Available!</b>\n\n"
        f"💰 <b>Service Price:</b> ${selling_price}\n"
        f"💰 <b>Your Balance:</b> ${user_balance:.2f}\n"
        f"📱 <b>Service:</b> {service_name}\n\n"
        "⚡ Checking wallet balance...",
        parse_mode='HTML'
    )

    # Step 3: Wallet-based purchase check
    if not wallet_system:
        await query.edit_message_text(
            "❌ <b>Wallet System Unavailable</b>\n\n"
            "Please contact administrator.",
            parse_mode='HTML'
        )
        return

    # Check if user has sufficient balance
    if not wallet_system.has_sufficient_balance(user.id, selling_price):
        needed_amount = selling_price - user_balance
        keyboard = [[
            InlineKeyboardButton("💰 Add Funds", callback_data="deposit_funds"),
            InlineKeyboardButton("🔙 Back", callback_data="start")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"💰 <b>Insufficient Balance</b>\n\n"
            f"💰 <b>Service Cost:</b> ${selling_price:.2f}\n"
            f"💰 <b>Your Balance:</b> ${user_balance:.2f}\n"
            f"💸 <b>Need:</b> ${needed_amount:.2f} more\n\n"
            f"💡 Add funds to your wallet to continue.\n"
            f"Minimum deposit: ${wallet_system.MIN_DEPOSIT_USD}",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return

    # User has sufficient balance - proceed with instant purchase (NO CONFIRMATION NEEDED)
    user_logger.info(
        "⚡ Instant purchase: User %s has sufficient balance ($%.2f)", user.id, user_balance)

    # Store service info for purchase
    if context.user_data is not None:
        context.user_data['selected_service_id'] = service_id
        context.user_data['selected_service_name'] = service_name
        context.user_data['selected_price'] = selling_price

    # AUTO-PROCESS purchase immediately without confirmation
    await query.edit_message_text(
        f"⚡ <b>Processing Purchase...</b>\n\n"
        f"📱 <b>Service:</b> {service_name}\n"
        f"💰 <b>Cost:</b> ${selling_price:.2f}\n"
        f"💰 <b>Your Balance:</b> ${user_balance:.2f}\n"
        f"💰 <b>After Purchase:</b> ${user_balance - selling_price:.2f}\n\n"
        f"🔄 <b>Processing instant purchase...</b>\n"
        f"📱 Service will be delivered automatically",
        parse_mode='HTML'
    )

    # Process the wallet purchase immediately
    await process_wallet_service_purchase(
        user_id=user.id,
        context=context,
        send_method=query.edit_message_text,
        service_id=service_id,
        service_name=service_name
    )

    if user:
        logger.info(
            "⚡ Auto-processed purchase for user %s: %s $%.2f", user.id, service_name, selling_price)
    else:
        logger.info(
            "⚡ Auto-processed purchase: %s $%.2f", service_name, selling_price)


# =============================================================================
# ORIGINAL CALLBACK QUERY HANDLERS
# =============================================================================


async def handle_buy_ring4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Ring4 purchase - now routes to service-specific flow"""
    if not update.effective_user:
        return

    user = update.effective_user

    # Check if this is a callback query or direct command
    if update.callback_query:
        query = update.callback_query
        await query.answer()  # Acknowledge callback immediately

        logger.info("🎯 Ring4 purchase request from user %s",
                    user.id if user else 'Unknown')

        # Route to the new service selection flow with Ring4 pre-selected
        # This ensures users get Ring4 specifically, not a fallback service
        await handle_service_purchase(update, context, 1574, "Ring4", 0.17)
    else:
        if not update.message:
            return
        # For direct messages, redirect to start menu with service selection
        await start_command(update, context)


async def handle_auto_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle auto-purchase callback from payment approval notification"""
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    try:
        # Parse callback data: "auto_purchase_{service_id}_{service_name}_{selling_price}"
        if not query.data:
            await query.edit_message_text("❌ Invalid purchase data.")
            return

        parts = query.data.split('_', 3)
        if len(parts) < 4:
            await query.edit_message_text("❌ Invalid purchase data.")
            return

        service_id = int(parts[2])
        # Split from the right to get price
        service_data = parts[3].rsplit('_', 1)
        service_name = service_data[0]
        selling_price = float(service_data[1])

        # Store in context
        if context.user_data is not None:
            context.user_data['selected_service_id'] = service_id
            context.user_data['selected_service_name'] = service_name
            context.user_data['selected_price'] = selling_price

        user_logger.info(
            "🚀 Auto-purchase initiated by user %s: %s ($%.2f)", user.id if user else 'Unknown', service_name, selling_price)

        # Execute the purchase
        await process_wallet_service_purchase(
            user.id if user else 0, context, query.edit_message_text, service_id, service_name
        )

    except RuntimeError as e:
        logger.error("Auto-purchase failed for user %s: %s",
                     user.id if user else 'Unknown', e)
        await query.edit_message_text(
            f"❌ <b>Auto-Purchase Failed</b>\n\n"
            f"Error: {str(e)[:100]}...\n\n"
            f"Please use /buy to browse services manually.",
            parse_mode='HTML'
        )


async def handle_service_unavailable(user_id: int, payment_id: Optional[str], context: ContextTypes.DEFAULT_TYPE, send_method, reason: str):
    """Handle cases where service cannot be provided and initiate refund"""

    logger.error("🚫 Service unavailable for user %s: %s", user_id, reason)

    # Notify user about service issue and automatic refund
    await send_method(
        f"❌ <b>Service Temporarily Unavailable</b>\n\n"
        f"🔧 <b>Issue:</b> {reason}\n"
        f"💰 <b>Refund:</b> Processing automatic refund\n"
        f"⏰ <b>Timeline:</b> 1-2 business days\n\n"
        f"🎯 We'll notify you when the service is restored.\n"
        f"💬 Contact admin if you need immediate assistance.\n\n"
        f"🆔 <b>Payment ID:</b> <code>{payment_id or 'N/A'}</code>",
        parse_mode='HTML'
    )

    # Notify all admins about service issue
    admin_message = (
        f"🚫 <b>SERVICE UNAVAILABLE ALERT</b>\n\n"
        f"👤 <b>User:</b> {user_id}\n"
        f"💰 <b>Payment ID:</b> <code>{payment_id or 'N/A'}</code>\n"
        f"⚠️ <b>Issue:</b> {reason}\n\n"
        f"🔧 <b>Action Required:</b>\n"
        f"• Check SMS Bot balance\n"
        f"• Top up account if needed\n"
        f"• Monitor service status\n"
        f"• Process refund if needed\n\n"
        f"🎯 Service quality is compromised!"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode='HTML'
            )
        except RuntimeError as e:
            logger.error("Failed to notify admin %s: %s", admin_id, str(e))

    # If we have a wallet system, handle refund
    if wallet_system:
        try:
            logger.info(
                "💰 Auto-refund initiated due to service unavailability")
        except RuntimeError as e:
            logger.error(
                "Error handling service unavailable refund: %s", str(e))


# Legacy payment function removed - now using wallet-based purchasing


async def process_wallet_service_purchase(user_id: int, context: ContextTypes.DEFAULT_TYPE, send_method, service_id: int, service_name: str):
    """Process service purchase using wallet balance"""

    # Get the selected price from user data
    selling_price = context.user_data.get(
        'selected_price', 0.15) if context.user_data else 0.15

    purchase_logger.info(
        "🚀 Starting wallet purchase for user %s: %s ($%.2f)", user_id, service_name, selling_price)

    start_time = asyncio.get_event_loop().time()
    order_id = None

    try:
        # Step 1: Reserve wallet balance (don't deduct yet - only when OTP received)
        if not wallet_system:
            await send_method("❌ Wallet system unavailable. Contact administrator.", parse_mode='HTML')
            return

        # Attempt to reserve balance
        order_id = f"ORD_{user_id}_{int(datetime.now().timestamp())}"
        reservation_success = wallet_system.reserve_balance(
            user_id=user_id,
            amount=selling_price,
            order_id=order_id,
            description=f"{service_name} service purchase"
        )

        if not reservation_success:
            user_balance = wallet_system.get_user_balance(user_id)
            await send_method(
                f"❌ <b>Insufficient Balance</b>\n\n"
                f"💰 Service Cost: ${selling_price:.2f}\n"
                f"💰 Your Balance: ${user_balance:.2f}\n"
                f"💸 Need: ${selling_price - user_balance:.2f} more\n\n"
                f"Please add funds to your wallet.",
                parse_mode='HTML'
            )
            return

        purchase_logger.info(
            "🔒 Wallet balance reserved for user %s: $%.2f (order: %s)", user_id, selling_price, order_id)

        # Step 2: Show processing message
        current_balance = wallet_system.get_user_balance(user_id)
        await send_method(
            f"⚡ <b>Processing {service_name} Purchase</b>\n\n"
            f"💰 Cost: ${selling_price:.2f} (reserved - will charge when OTP received)\n"
            f"💰 Current Balance: ${current_balance:.2f}\n"
            f"📱 Service: {service_name}\n"
            f"🔄 Acquiring your number...\n\n"
            f"💡 <b>Note:</b> You'll only be charged when you receive the OTP code!",
            parse_mode='HTML'
        )

        if not sms_api:
            # Cancel reservation and show error
            wallet_system.cancel_reservation(
                user_id, selling_price, order_id, "SMS API unavailable")
            await send_method("❌ SMS service unavailable. No charge to your wallet.", parse_mode='HTML')
            return

        # Step 3: Validate API balance
        try:
            balance_result = await sms_api.check_balance()
        except (AttributeError, RuntimeError):
            # Cancel reservation
            wallet_system.cancel_reservation(
                user_id, selling_price, order_id, "Provider balance check failed")
            await send_method("❌ Service provider unavailable. No charge to your wallet.", parse_mode='HTML')
            return

        if isinstance(balance_result, Exception) or not balance_result.get('success'):
            # Cancel reservation
            wallet_system.cancel_reservation(
                user_id, selling_price, order_id, "Provider balance check failed")
            await send_method("❌ Service provider unavailable. No charge to your wallet.", parse_mode='HTML')
            return

        current_balance = float(balance_result.get('balance', '0.0'))
        estimated_cost = selling_price * 0.8  # 80% safety margin

        if current_balance < estimated_cost:
            # Cancel reservation
            wallet_system.cancel_reservation(
                user_id, selling_price, order_id, "Provider insufficient balance")
            await send_method(
                f"❌ Service temporarily unavailable (provider balance: ${current_balance:.2f}). "
                f"No charge to your wallet.",
                parse_mode='HTML'
            )
            return

        # Step 4: Purchase the service
        purchase_logger.info(
            "🛒 Executing %s purchase for user %s", service_name, user_id)

        await send_method(
            f"🔄 <b>Acquiring {service_name} Number...</b>\n\n"
            f"💰 Payment: ${selling_price:.2f} (reserved)\n"
            f"📞 Requesting number from provider...\n"
            f"⏱️ This may take a few seconds...\n\n"
            f"💡 <b>Remember:</b> Payment only processed when OTP is received!",
            parse_mode='HTML'
        )

        # Execute the purchase based on service type
        if service_id == RING4_SERVICE_ID:
            result = await sms_api.purchase_ring4_number()
        else:
            result = await sms_api.purchase_specific_service(service_id, service_name)

        # Step 5: Process purchase result
        if result['success']:
            purchase_logger.info(
                "✅ %s number acquired successfully for user %s", service_name, user_id)

            # Create order record (don't charge yet)
            actual_order_id = result.get('order_id', order_id)
            order_data = {
                'user_id': user_id,
                'service_id': service_id,
                'service_name': service_name,
                'number': result['number'],
                'order_id': actual_order_id,
                'cost': selling_price,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=ORDER_EXPIRES_IN)).isoformat(),
                'country_id': 1,  # Default to US for legacy function
                'country_name': 'United States',
                'country_flag': '🇺🇸',
                'reservation_order_id': order_id  # Track our reservation
            }

            db_order_id = db.create_order(user_id, order_data)

            # Update with actual order ID
            if 'order_id' in result:
                db.update_order_status(db_order_id, 'pending')

            # Create cancel/refund buttons for the order
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 Get Different Number", callback_data=f"instant_refund_reorder_{actual_order_id}"),
                ],
                [
                    InlineKeyboardButton(
                        "🚫 Cancel Order", callback_data=f"cancel_order_{actual_order_id}"),
                    InlineKeyboardButton(
                        "💰 Request Refund", callback_data=f"refund_{actual_order_id}")
                ],
                [
                    InlineKeyboardButton(
                        "📱 Check Balance", callback_data="show_balance"),
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_to_start")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Success message with action buttons (not charged yet)
            await send_method(
                f"✅ <b>{service_name} Number Acquired!</b>\n\n"
                f"📱 <b>Your Number:</b> <code>{result['number']}</code>\n"
                f"💰 <b>Cost:</b> ${selling_price:.2f} (reserved - will charge when OTP received)\n"
                f"💰 <b>Wallet Balance:</b> ${current_balance:.2f}\n"
                f"🆔 <b>Order ID:</b> <code>{actual_order_id}</code>\n"
                f"⏰ <b>Valid for:</b> 10 minutes\n\n"
                f"🔔 <b>Waiting for SMS...</b>\n"
                f"OTP will be delivered automatically when received.\n\n"
                f"💡 <b>Payment:</b> You'll only be charged when you receive the OTP code!\n"
                f"Use the buttons below for order management.",
                parse_mode='HTML',
                reply_markup=reply_markup
            )

            # Start OTP polling
            start_otp_polling(actual_order_id, user_id, context)

            purchase_logger.info(
                "🎉 Number acquisition completed for user %s: %s | Order: %s | Payment reserved",
                user_id, service_name, actual_order_id
            )

        else:
            # Purchase failed - cancel reservation
            error_msg = result.get('message', 'Unknown error')
            purchase_logger.error(
                "❌ %s purchase failed for user %s: %s", service_name, user_id, error_msg)

            # Cancel reservation
            cancel_success = wallet_system.cancel_reservation(
                user_id, selling_price, order_id, f"Purchase failed: {error_msg}")

            cancel_text = " No charge to your wallet." if cancel_success else " Please contact support."

            await send_method(
                f"❌ <b>Purchase Failed</b>\n\n"
                f"Service: {service_name}\n"
                f"Error: {error_msg}\n"
                f"💰 ${selling_price:.2f}{cancel_text}",
                parse_mode='HTML'
            )

    except RuntimeError as e:
        purchase_logger.error(
            "❌ Critical error in wallet purchase for user %s: %s", user_id, str(e))

        # Attempt to cancel reservation on any error
        if 'order_id' in locals() and order_id and wallet_system:
            try:
                wallet_system.cancel_reservation(
                    user_id, selling_price, order_id, f"System error: {str(e)}")
                cancel_text = " No charge to your wallet."
            except (OSError, RuntimeError):
                cancel_text = " Please contact support."
        else:
            cancel_text = ""

        await send_method(
            f"❌ <b>System Error</b>\n\n"
            f"An error occurred during purchase.{cancel_text}\n"
            f"Please try again or contact support.",
            parse_mode='HTML'
        )

    finally:
        end_time = asyncio.get_event_loop().time()
        performance_logger.info(
            "⏱️ Purchase processing completed in %.2fs", end_time - start_time)


# =============================================================================
# OTP & ORDER STATUS HANDLERS
# =============================================================================
# OTP & ORDER STATUS HANDLERS
# =============================================================================


async def handle_refund_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle refund request - AUTO APPROVAL"""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user_id = query.from_user.id

    await query.answer()

    try:
        if not query.data:
            await query.edit_message_text("❌ Invalid request data.")
            return

        # Extract order_id from callback data (format: "refund_{order_id}")
        # Keep as string, don't convert to int
        order_id = query.data.split('_', 1)[1]

        # Verify order belongs to user and is refundable
        order = db.get_order(order_id)
        if not order or order['user_id'] != user_id:
            await query.edit_message_text("❌ Order not found or access denied.")
            return

        if order['status'] not in ['pending', 'timeout', 'error', 'cancelled']:
            await query.edit_message_text(
                f"❌ Order #{order_id} is not eligible for refund.\n"
                f"Current status: {order['status']}"
            )
            return

        # CRITICAL SECURITY CHECK: Prevent duplicate refunds
        if order['status'] == 'refunded':
            await query.edit_message_text(
                f"❌ <b>Already Refunded</b>\n\n"
                f"Order #{order_id} has already been refunded.\n"
                f"Check your wallet balance or order history."
            )
            logger.warning(
                "🚨 DUPLICATE REFUND ATTEMPT: User %s tried to refund already refunded order %s",
                user_id, order_id
            )
            return

        # AUTOMATICALLY PROCESS REFUND (No admin approval needed)
        if wallet_system:
            refund_success = wallet_system.process_refund(
                user_id=user_id,
                refund_amount=order['cost'],
                order_id=str(order_id),
                reason="User requested refund - auto approved"
            )

            if refund_success:
                # Update order status to refunded
                db.update_order_status(order_id, 'refunded')

                # Cancel order with SMS Bot if available
                if sms_api:
                    try:
                        cancel_result = await sms_api.cancel_order(str(order_id))
                        if cancel_result.get('success'):
                            logger.info(
                                "✅ User refund order %s cancelled with SMS Bot", order_id)
                        else:
                            logger.warning(
                                "⚠️ Failed to cancel user refund order %s with SMS Bot", order_id)
                    except Exception as cancel_error:
                        logger.error(
                            "❌ Error cancelling user refund order %s: %s", order_id, cancel_error)

                # Get updated balance
                user_balance = wallet_system.get_user_balance(user_id)

                await query.edit_message_text(
                    f"✅ <b>Refund Processed</b>\n\n"
                    f"🆔 <b>Order:</b> #{order_id}\n"
                    f"💰 <b>Refund Amount:</b> ${order['cost']}\n"
                    f"💰 <b>New Balance:</b> ${user_balance:.2f}\n\n"
                    f"✅ Your refund has been automatically processed and added to your wallet.\n"
                    f"You can use your balance for new orders anytime.\n\n"
                    f"💡 Quick tip: Use 'Order Again' to reorder the same service instantly!",
                    parse_mode='HTML',
                    reply_markup=create_order_again_keyboard(order_id, order)
                )

                logger.info(
                    "✅ Auto-approved refund for order %s, user %s, amount $%.2f",
                    order_id, user_id, order['cost']
                )
            else:
                await query.edit_message_text(
                    f"❌ <b>Refund Failed</b>\n\n"
                    f"Failed to process refund for order #{order_id}.\n"
                    f"Please try again or contact support.",
                    parse_mode='HTML'
                )
                logger.error(
                    "❌ Auto-refund failed for order %s, user %s", order_id, user_id)
        else:
            await query.edit_message_text(
                f"❌ <b>Wallet System Unavailable</b>\n\n"
                f"Refund system is currently unavailable.\n"
                f"Please contact support for manual processing.",
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error("❌ Error processing auto-refund: %s", str(e))
        await query.edit_message_text(
            f"❌ <b>Refund Error</b>\n\n"
            f"An error occurred while processing your refund.\n"
            f"Please try again or contact support.",
            parse_mode='HTML'
        )


async def handle_instant_refund_and_reorder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle instant refund and reorder request - cancels current order and places new one with same settings"""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user_id = query.from_user.id
    await query.answer()

    try:
        if not query.data:
            await query.edit_message_text("❌ Invalid request data.")
            return

        # Extract order_id from callback data (format: "instant_refund_reorder_{order_id}")
        order_id = query.data.split('_', 3)[3]

        # Verify order belongs to user and is eligible for instant refund
        order = db.get_order(order_id)
        if not order or order['user_id'] != user_id:
            await query.edit_message_text("❌ Order not found or access denied.")
            return

        # Check if order is in valid state for instant refund
        if order['status'] not in ['pending', 'timeout', 'error']:
            await query.edit_message_text(
                f"❌ <b>Cannot Process Instant Refund</b>\n\n"
                f"Order #{order_id} status: {order['status']}\n"
                f"Instant refund is only available for pending orders.\n\n"
                f"Use regular refund if the order is completed or cancelled.",
                parse_mode='HTML'
            )
            return

        # CRITICAL SECURITY CHECK: Prevent duplicate refunds
        if order['status'] == 'refunded':
            await query.edit_message_text(
                f"❌ <b>Already Refunded</b>\n\n"
                f"Order #{order_id} has already been refunded.\n"
                f"Check your wallet balance or order history.",
                parse_mode='HTML'
            )
            logger.warning(
                "🚨 DUPLICATE INSTANT REFUND ATTEMPT: User %s tried to refund already refunded order %s",
                user_id, order_id
            )
            return

        # Get order details for reorder
        service_id = order.get('service_id', 1574)  # Default to Ring4
        service_name = order.get('service_name', 'Ring4')
        country_id = order.get('country_id', 1)  # Default to US
        country_name = order.get('country_name', 'United States')
        country_flag = order.get('country_flag', '🇺🇸')
        order_cost = float(order.get('cost', 0))

        # Critical validation: Ensure service_id is valid
        if service_id is None:
            logger.error(
                "🚨 CRITICAL: service_id is None for order %s, forcing to Ring4", order_id)
            service_id = 1574
            service_name = 'Ring4'

        # Log the extracted values for debugging
        logger.info("📊 Instant refund for order %s: service_id=%s, service_name=%s, country_id=%s",
                    order_id, service_id, service_name, country_id)

        if not wallet_system or not sms_api:
            await query.edit_message_text(
                "❌ <b>System Unavailable</b>\n\n"
                "Instant refund and reorder system is currently unavailable.\n"
                "Please try regular refund or contact support.",
                parse_mode='HTML'
            )
            return

        # Step 1: Show processing message
        await query.edit_message_text(
            f"🔄 <b>Processing Instant Number Replacement</b>\n\n"
            f"🆔 <b>Current Order:</b> #{order_id}\n"
            f"📱 <b>Service:</b> {service_name}\n"
            f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
            f"💰 <b>Amount:</b> ${order_cost:.2f}\n\n"
            f"⏳ Step 1/4: Verifying new number availability...",
            parse_mode='HTML'
        )

        # Step 2: FIRST check if new order can be placed (CRITICAL - do this BEFORE refunding)
        try:
            # Check service availability first
            availability_check = await sms_api.check_service_availability(service_id, country_id)
            if not availability_check or availability_check == 0:
                await query.edit_message_text(
                    f"❌ <b>Service Unavailable</b>\n\n"
                    f"📱 <b>Service:</b> {service_name}\n"
                    f"🌍 <b>Country:</b> {country_flag} {country_name}\n\n"
                    f"This service is temporarily unavailable.\n"
                    f"Your current order #{order_id} remains active.\n\n"
                    f"💡 Try a different service or use regular refund.",
                    parse_mode='HTML'
                )
                return

            # Step 3: Cancel current order with SMSPool (use our fixed API)
            await query.edit_message_text(
                f"🔄 <b>Processing Instant Number Replacement</b>\n\n"
                f"🆔 <b>Current Order:</b> #{order_id}\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"💰 <b>Amount:</b> ${order_cost:.2f}\n\n"
                f"⏳ Step 2/4: Cancelling current order...",
                parse_mode='HTML'
            )

            # Cancel the polling task FIRST to prevent status update notifications
            if order_id in active_polls:
                active_polls[order_id].cancel()
                del active_polls[order_id]
                logger.info(
                    "🛑 Cancelled active polling for order %s before instant refund", order_id)

            # Cancel with SMS provider using our fixed API
            api_refund_success = False
            try:
                cancel_result = await sms_api.cancel_order(str(order_id))

                # Our fixed SMS Bot API now returns reliable results
                if cancel_result.get('success', False):
                    api_refund_success = True
                    logger.info(
                        "✅ Order %s successfully cancelled with SMS Bot API for instant reorder", order_id)
                else:
                    logger.warning(
                        "⚠️ SMS Bot API did not confirm cancellation for order %s: %s",
                        order_id, cancel_result.get('message', 'Unknown error'))
            except Exception as cancel_error:
                logger.warning(
                    "⚠️ Error cancelling order %s for instant reorder: %s", order_id, cancel_error)

            # Step 4: Process new order (only if cancellation succeeded or to prevent user loss)
            await query.edit_message_text(
                f"🔄 <b>Processing Instant Number Replacement</b>\n\n"
                f"🆔 <b>Current Order:</b> #{order_id}\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"💰 <b>Amount:</b> ${order_cost:.2f}\n\n"
                f"⏳ Step 3/4: Getting your new number...",
                parse_mode='HTML'
            )

            # Purchase new number using the proven working method
            purchase_result = await sms_api.purchase_specific_service(service_id, service_name, country_id)

            if not purchase_result.get('success'):
                # New order failed - current order still active
                error_msg = clean_html_message(
                    purchase_result.get('message', 'Unknown error'))
                await query.edit_message_text(
                    f"❌ <b>New Number Purchase Failed</b>\n\n"
                    f"🆔 <b>Current Order:</b> #{order_id} (still active)\n"
                    f"❌ <b>Error:</b> {error_msg}\n\n"
                    f"Your current order remains active and unchanged.\n"
                    f"You can use regular refund or try again later.",
                    parse_mode='HTML'
                )
                return

            # Step 5: New order successful - now handle refund based on API confirmation
            new_order_id = purchase_result.get('order_id')
            new_phone_number = purchase_result.get('number')

            await query.edit_message_text(
                f"🔄 <b>Processing Instant Number Replacement</b>\n\n"
                f"✅ <b>New Number:</b> <code>{new_phone_number}</code>\n"
                f"🆔 <b>New Order:</b> #{new_order_id}\n\n"
                f"⏳ Step 4/4: Finalizing replacement...",
                parse_mode='HTML'
            )

            # Process original order cancellation based on API result and reservation system
            cancel_success = False

            # Get the original order to check if it has a reservation
            original_order = db.get_order(order_id)
            reservation_order_id = original_order.get(
                'reservation_order_id') if original_order else None

            if api_refund_success:
                # API successfully cancelled - just cancel the reservation (no wallet refund needed)
                if reservation_order_id:
                    cancel_success = wallet_system.cancel_reservation(
                        user_id=user_id,
                        amount=order_cost,
                        order_id=str(order_id),
                        reason="Instant replacement - API cancelled original order"
                    )
                    logger.info(
                        f"✅ Order {order_id} cancelled by SMS Bot API - reservation cancelled")
                else:
                    # Old order without reservation - already charged, no action needed
                    cancel_success = True
                    logger.info(
                        f"✅ Order {order_id} refunded by SMS Bot API - no wallet action needed")
            else:
                # API refund failed or unconfirmed
                if reservation_order_id:
                    # Cancel the reservation since no actual charge occurred
                    cancel_success = wallet_system.cancel_reservation(
                        user_id=user_id,
                        amount=order_cost,
                        order_id=str(order_id),
                        reason="Instant replacement - API refund failed, cancelling reservation"
                    )
                    logger.info(
                        f"⚠️ API refund failed for order {order_id} - cancelled reservation (no charge occurred)")
                else:
                    # Old order without reservation - may need actual refund
                    cancel_success = wallet_system.process_refund(
                        user_id=user_id,
                        refund_amount=order_cost,
                        order_id=str(order_id),
                        reason="Instant replacement - legacy order refund"
                    )
                    logger.warning(
                        f"⚠️ SMS Bot API refund failed for legacy order {order_id} - processed wallet refund")

            if not cancel_success:
                # This is a critical error - we have two reservations/orders now
                logger.error(
                    "🚨 CRITICAL: Failed to handle original order %s after new order %s placed", order_id, new_order_id)

                # Try to cancel the new order to avoid double reservation
                try:
                    await sms_api.cancel_order(str(new_order_id))
                    # Also cancel the new order's reservation
                    wallet_system.cancel_reservation(
                        user_id=user_id,
                        amount=order_cost,
                        order_id=str(new_order_id),
                        reason="Cancelling new order due to original order handling failure"
                    )
                except:
                    pass

                await query.edit_message_text(
                    f"❌ <b>Critical Error</b>\n\n"
                    f"Failed to process original order #{order_id}.\n"
                    f"New order #{new_order_id} has been cancelled.\n\n"
                    f"Please contact support immediately.\n"
                    f"Reference: Order handling error",
                    parse_mode='HTML'
                )
                return

            # Update original order status based on what happened
            if api_refund_success or reservation_order_id:
                # Cancelled, not refunded (no charge occurred)
                db.update_order_status(order_id, 'cancelled')
            else:
                # Actually refunded (legacy order)
                db.update_order_status(order_id, 'refunded')

            # Create new order in database with reservation system
            new_order_data = {
                'order_id': new_order_id,
                'number': new_phone_number,
                'cost': order_cost,
                'service_name': service_name,
                'service_id': service_id,
                'country_id': country_id,
                'country_name': country_name,
                'country_flag': country_flag,
                # New reservation for new order
                'reservation_order_id': f"ORD_{user_id}_{int(datetime.now().timestamp())}"
            }

            db.create_order(user_id, new_order_data)

            # Reserve balance for new order (will charge when OTP received)
            reservation_success = wallet_system.reserve_balance(
                user_id=user_id,
                amount=order_cost,
                order_id=str(new_order_id),
                description=f"Instant number replacement - {service_name} ({country_name})"
            )

            if not reservation_success:
                # Critical error - cancel the new order and notify user
                try:
                    await sms_api.cancel_order(str(new_order_id))
                except:
                    pass

                await query.edit_message_text(
                    f"❌ <b>Insufficient Balance for Replacement</b>\n\n"
                    f"New order #{new_order_id} has been cancelled.\n"
                    f"Original order #{order_id} remains active.\n\n"
                    f"Please add funds to your wallet and try again.",
                    parse_mode='HTML'
                )
                return

            # Get updated balance
            user_balance = wallet_system.get_user_balance(user_id)

            # Create buttons for the new order
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 Get Different Number", callback_data=f"instant_refund_reorder_{new_order_id}"),
                ],
                [
                    InlineKeyboardButton(
                        "💰 Instant Refund", callback_data=f"refund_{new_order_id}"),
                    InlineKeyboardButton(
                        "❌ Cancel Order", callback_data=f"cancel_order_{new_order_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send success message with new number and status
            refund_status_msg = ""
            if api_refund_success:
                refund_status_msg = "✅ <b>SMS Bot:</b> Original order cancelled by API\n"
            elif reservation_order_id:
                refund_status_msg = "✅ <b>Wallet:</b> Original order reservation cancelled (no charge occurred)\n"
            else:
                refund_status_msg = "💰 <b>Wallet:</b> Original order refunded (legacy order)\n"

            await query.edit_message_text(
                f"🎉 <b>Number Successfully Replaced!</b>\n\n"
                f"📱 <b>Your New Number:</b> <code>{new_phone_number}</code>\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"💰 <b>Cost:</b> ${order_cost:.2f} (reserved - will charge when OTP received)\n"
                f"💰 <b>Wallet Balance:</b> ${user_balance:.2f}\n"
                f"🆔 <b>New Order ID:</b> <code>{new_order_id}</code>\n\n"
                f"⏰ <b>Valid for 10 minutes</b>\n"
                f"🔄 <b>OTP monitoring started</b>\n\n"
                f"✨ <b>Replaced order #{order_id}</b>\n"
                f"💡 <b>Payment:</b> You'll only be charged when you receive the OTP code!\n"
                f"{refund_status_msg}"
                f"Use this number for verification. You'll get the OTP automatically!",
                parse_mode='HTML',
                reply_markup=reply_markup
            )

            # Start OTP polling for new order
            if new_order_id:
                start_otp_polling(new_order_id, user_id, context)

            logger.info(
                "✅ Instant number replacement completed for user %s: Order %s -> Order %s (Service: %s, Country: %s) - API refund: %s",
                user_id, order_id, new_order_id, service_name, country_name,
                "confirmed" if api_refund_success else "wallet processed"
            )

        except Exception as purchase_error:
            logger.error("❌ Error during number replacement: %s",
                         str(purchase_error))
            error_msg = clean_html_message(str(purchase_error))[:100]
            await query.edit_message_text(
                f"❌ <b>Number Replacement Failed</b>\n\n"
                f"🆔 <b>Current Order:</b> #{order_id} (still active)\n"
                f"❌ <b>Error:</b> {error_msg}\n\n"
                f"Your current order remains unchanged.\n"
                f"Please try again or use regular refund.\n\n"
                f"💡 All systems are working normally.",
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(
            "❌ Error processing instant number replacement: %s", str(e))
        error_msg = clean_html_message(str(e))[:100]
        await query.edit_message_text(
            f"❌ <b>System Error</b>\n\n"
            f"An error occurred while processing your request.\n"
            f"Your current order remains unchanged.\n\n"
            f"Please try again or use regular refund.\n"
            f"Error: {error_msg}",
            parse_mode='HTML'
        )


async def handle_refund_and_reorder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle refund request with immediate reorder using same service and country"""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user_id = query.from_user.id
    await query.answer()

    try:
        if not query.data:
            await query.edit_message_text("❌ Invalid request data.")
            return

        # Extract order_id from callback data (format: "refund_reorder_{order_id}")
        order_id = query.data.split('_', 2)[2]

        # Verify order belongs to user and is refundable
        order = db.get_order(order_id)
        if not order or order['user_id'] != user_id:
            await query.edit_message_text("❌ Order not found or access denied.")
            return

        if order['status'] not in ['pending', 'timeout', 'error', 'cancelled']:
            await query.edit_message_text(
                f"❌ Order #{order_id} is not eligible for refund.\n"
                f"Current status: {order['status']}"
            )
            return

        # CRITICAL SECURITY CHECK: Prevent duplicate refunds
        if order['status'] == 'refunded':
            await query.edit_message_text(
                f"❌ <b>Already Refunded</b>\n\n"
                f"Order #{order_id} has already been refunded.\n"
                f"Check your wallet balance or order history.",
                parse_mode='HTML'
            )
            logger.warning(
                "🚨 DUPLICATE REFUND ATTEMPT: User %s tried to refund and reorder already refunded order %s",
                user_id, order_id
            )
            return

        # Get order details for reorder
        service_id = order.get('service_id', 1574)  # Default to Ring4
        service_name = order.get('service_name', 'Ring4')
        country_id = order.get('country_id', 1)  # Default to US
        country_name = order.get('country_name', 'United States')
        country_flag = order.get('country_flag', '🇺🇸')
        order_cost = float(order.get('cost', 0))

        if not wallet_system or not sms_api:
            await query.edit_message_text(
                "❌ <b>System Unavailable</b>\n\n"
                "Refund and reorder system is currently unavailable.\n"
                "Please try regular refund or contact support.",
                parse_mode='HTML'
            )
            return

        # Step 1: Show processing message
        await query.edit_message_text(
            f"🔄 <b>Processing Refund & Reorder</b>\n\n"
            f"🆔 <b>Cancelling Order:</b> #{order_id}\n"
            f"📱 <b>Service:</b> {service_name}\n"
            f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
            f"💰 <b>Amount:</b> ${order_cost:.2f}\n\n"
            f"⏳ Step 1/3: Cancelling order and verifying refund...",
            parse_mode='HTML'
        )

        # Step 2: Cancel with SMS provider using our fixed API
        api_refund_success = False

        if sms_api:
            try:
                # Cancel the order using our fixed SMS Bot API
                cancel_result = await sms_api.cancel_order(str(order_id))

                # Our fixed SMS Bot API now returns reliable results
                if cancel_result.get('success', False):
                    api_refund_success = True
                    logger.info(
                        "✅ Order %s successfully cancelled with SMS Bot API for reorder", order_id)
                else:
                    logger.warning(
                        "⚠️ SMS Bot API did not confirm cancellation for order %s: %s",
                        order_id, cancel_result.get('message', 'Unknown error'))
            except Exception as cancel_error:
                logger.warning(
                    "⚠️ Error cancelling order %s for reorder: %s", order_id, cancel_error)

        # Step 3: Process wallet refund only if API refund failed
        refund_success = False
        if api_refund_success:
            # API successfully cancelled and refunded - no wallet refund needed
            logger.info(
                f"✅ Order {order_id} refunded by SMS Bot API - no wallet refund needed")
            refund_success = True
        else:
            # API refund failed - process wallet refund to protect user
            logger.warning(
                f"⚠️ SMS Bot API refund failed for order {order_id} - processing wallet refund")
            refund_success = wallet_system.process_refund(
                user_id=user_id,
                refund_amount=order_cost,
                order_id=str(order_id),
                reason="Refund & reorder - wallet refund (API refund failed)"
            )

        if not refund_success:
            await query.edit_message_text(
                f"❌ <b>Refund Failed</b>\n\n"
                f"Failed to process refund for order #{order_id}.\n"
                f"Please try regular refund or contact support.",
                parse_mode='HTML'
            )
            return

        # Update original order status to refunded
        db.update_order_status(order_id, 'refunded')

        # Step 4: Show reorder progress with refund status
        refund_status_msg = ""
        if api_refund_success:
            refund_status_msg = "✅ <b>SMS Bot Refund:</b> Confirmed\n"
        else:
            refund_status_msg = "💰 <b>Wallet Refund:</b> Processed\n"

        await query.edit_message_text(
            f"✅ <b>Refund Completed!</b>\n\n"
            f"🆔 <b>Refunded Order:</b> #{order_id}\n"
            f"💰 <b>Amount:</b> ${order_cost:.2f}\n"
            f"{refund_status_msg}\n"
            f"⏳ Step 2/3: Ordering new {service_name} number for {country_flag} {country_name}...",
            parse_mode='HTML'
        )

        # Step 5: Set context for new purchase
        if context.user_data is not None:
            context.user_data['selected_service_id'] = service_id
            context.user_data['selected_country_id'] = country_id
            context.user_data['selected_price'] = order_cost

        # Step 6: Process new purchase
        await process_wallet_purchase(
            user_id=user_id,
            context=context,
            send_method=query.edit_message_text,
            service_id=service_id,
            service_name=service_name,
            selling_price=order_cost
        )

        logger.info(
            "✅ Refund & reorder completed for user %s: Order %s -> New order (Service: %s, Country: %s) - API refund: %s",
            user_id, order_id, service_name, country_name,
            "confirmed" if api_refund_success else "wallet processed"
        )

    except Exception as e:
        logger.error("❌ Error processing refund & reorder: %s", str(e))
        await query.edit_message_text(
            f"❌ <b>Refund & Reorder Error</b>\n\n"
            f"An error occurred while processing your request.\n"
            f"Please try regular refund or contact support.\n\n"
            f"Error: {str(e)[:100]}",
            parse_mode='HTML'
        )


async def handle_order_again(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order again request - automatically reorder using same service and country from previous order"""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user_id = query.from_user.id
    await query.answer()

    try:
        if not query.data:
            await query.edit_message_text("❌ Invalid request data.")
            return

        # Extract order_id from callback data (format: "order_again_{order_id}")
        order_id = query.data.split('_', 2)[2]

        # Get original order details
        order = db.get_order(order_id)
        if not order or order['user_id'] != user_id:
            await query.edit_message_text("❌ Order not found or access denied.")
            return

        # Extract service details from original order
        service_id = order.get('service_id', 1574)  # Default to Ring4
        service_name = order.get('service_name', 'Ring4')
        country_id = order.get('country_id', 1)  # Default to US
        country_name = order.get('country_name', 'United States')
        country_flag = order.get('country_flag', '🇺🇸')
        order_cost = float(order.get('cost', 0.15))

        # Critical validation: Ensure service_id is valid
        if service_id is None:
            logger.error(
                "🚨 CRITICAL: service_id is None for order %s, forcing to Ring4", order_id)
            service_id = 1574
            service_name = 'Ring4'

        logger.info("🔄 Order again for user %s: service_id=%s, service_name=%s, country_id=%s",
                    user_id, service_id, service_name, country_id)

        if not wallet_system or not sms_api:
            await query.edit_message_text(
                "❌ <b>System Unavailable</b>\n\n"
                "Order system is currently unavailable.\n"
                "Please try again later or contact support.",
                parse_mode='HTML'
            )
            return

        # Check user wallet balance
        user_balance = wallet_system.get_user_balance(user_id)
        if user_balance < order_cost:
            await query.edit_message_text(
                f"❌ <b>Insufficient Balance</b>\n\n"
                f"💰 <b>Service Cost:</b> ${order_cost:.2f}\n"
                f"💰 <b>Your Balance:</b> ${user_balance:.2f}\n"
                f"💸 <b>Need:</b> ${order_cost - user_balance:.2f} more\n\n"
                f"Please add funds to your wallet first.",
                parse_mode='HTML'
            )
            return

        # Show processing message
        await query.edit_message_text(
            f"🔄 <b>Ordering Again</b>\n\n"
            f"📱 <b>Service:</b> {service_name}\n"
            f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
            f"💰 <b>Price:</b> ${order_cost:.2f}\n\n"
            f"⏳ Step 1/3: Checking service availability...",
            parse_mode='HTML'
        )

        # Check service availability first
        try:
            availability_check = await sms_api.check_service_availability(service_id, country_id)
            if not availability_check or availability_check == 0:
                await query.edit_message_text(
                    f"❌ <b>Service Unavailable</b>\n\n"
                    f"📱 <b>Service:</b> {service_name}\n"
                    f"🌍 <b>Country:</b> {country_flag} {country_name}\n\n"
                    f"This service is temporarily unavailable.\n"
                    f"Please try a different service or try again later.\n\n"
                    f"💡 Use /buy to browse available services.",
                    parse_mode='HTML'
                )
                return

            # Service available - proceed with purchase
            await query.edit_message_text(
                f"✅ <b>Service Available!</b>\n\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"💰 <b>Price:</b> ${order_cost:.2f}\n\n"
                f"⏳ Step 2/3: Processing payment...",
                parse_mode='HTML'
            )

            # Set context for purchase
            if context.user_data is not None:
                context.user_data['selected_service_id'] = service_id
                context.user_data['selected_country_id'] = country_id
                context.user_data['selected_price'] = order_cost

            # Process the purchase using wallet
            await process_wallet_service_purchase_with_country(
                user_id=user_id,
                context=context,
                send_method=query.edit_message_text,
                service_id=service_id,
                service_name=service_name,
                country_id=country_id,
                country_name=country_name,
                country_flag=country_flag
            )

            logger.info(
                "✅ Order again completed for user %s: Service %s in %s ($%.2f)",
                user_id, service_name, country_name, order_cost
            )

        except Exception as purchase_error:
            logger.error("❌ Error during order again: %s", str(purchase_error))
            error_msg = clean_html_message(str(purchase_error))[:100]
            await query.edit_message_text(
                f"❌ <b>Order Failed</b>\n\n"
                f"📱 <b>Service:</b> {service_name}\n"
                f"🌍 <b>Country:</b> {country_flag} {country_name}\n"
                f"❌ <b>Error:</b> {error_msg}\n\n"
                f"Please try again or use /buy for different services.\n\n"
                f"💡 Your wallet balance was not deducted.",
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error("❌ Error processing order again: %s", str(e))
        error_msg = clean_html_message(str(e))[:100]
        await query.edit_message_text(
            f"❌ <b>System Error</b>\n\n"
            f"An error occurred while processing your request.\n"
            f"Please try again or contact support.\n\n"
            f"Error: {error_msg}",
            parse_mode='HTML'
        )


def create_order_again_keyboard(order_id, order):
    """Create keyboard with Order Again button if service details are available"""
    keyboard = []

    keyboard.extend([
        [
            InlineKeyboardButton("📱 Browse Services",
                                 callback_data="browse_services"),
            InlineKeyboardButton("💰 Balance", callback_data="show_balance")
        ],
        [
            InlineKeyboardButton("🔙 Main Menu", callback_data="start_menu")
        ]
    ])

    # Add Order Again button at the bottom if we have service details
    if order.get('service_id') and order.get('country_id'):
        service_name = order.get('service_name', 'Same Service')
        country_flag = order.get('country_flag', '🌍')
        keyboard.append([
            InlineKeyboardButton(
                f"🔄 Order Again ({service_name} in {country_flag})",
                callback_data=f"order_again_{order_id}"
            )
        ])

    return InlineKeyboardMarkup(keyboard)


async def show_admin_refunds(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Show pending refunds to admin"""
    if not update.effective_user:
        return

    user_id = update.effective_user.id

    if not is_admin(user_id):
        if update.callback_query:
            await update.callback_query.answer("❌ Access denied.")
        return

    pending_refunds = db.get_pending_refunds()

    if not pending_refunds:
        text = "💰 <b>No Pending Refunds</b>\n\nAll refund requests have been processed."
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode='HTML')
        elif update.message:
            await update.message.reply_text(text, parse_mode='HTML')
        return

    keyboard = []
    for refund in pending_refunds:
        order = db.get_order(refund['order_id'])
        if order:
            keyboard.append([
                InlineKeyboardButton(
                    f"Order #{refund['order_id']} - ${order['cost']}",
                    callback_data=f"refund_details_{refund['order_id']}"
                )
            ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"💰 <b>Pending Refunds ({len(pending_refunds)})</b>\n\n"
        f"Select a refund to process:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)


async def handle_refund_details(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Show refund details to admin"""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ Access denied.")
        return

    await query.answer()

    try:
        if not query.data:
            await query.edit_message_text("❌ Invalid request data.")
            return

        # Keep as string, don't convert to int
        # Join everything after 'refund_details_'
        order_id = '_'.join(query.data.split('_')[2:])
        order = db.get_order(order_id)

        if not order:
            await query.edit_message_text("❌ Order not found.")
            return

        keyboard = [[
            InlineKeyboardButton("✅ Approve Refund",
                                 callback_data=f"approve_refund_{order_id}"),
            InlineKeyboardButton(
                "❌ Deny Refund", callback_data=f"deny_refund_{order_id}")
        ], [
            InlineKeyboardButton("← Back to Refunds",
                                 callback_data="admin_refunds")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        created = datetime.fromisoformat(
            order['created_at']).strftime('%Y-%m-%d %H:%M:%S')

        details_text = (
            f"💰 <b>Refund Request Details</b>\n\n"
            f"📱 <b>Order:</b> #{order_id}\n"
            f"👤 <b>User:</b> {order['user_id']}\n"
            f"📞 <b>Number:</b> {order['number']}\n"
            f"💰 <b>Cost:</b> ${order['cost']}\n"
            f"🔄 <b>Status:</b> {order['status']}\n"
            f"📅 <b>Created:</b> {created}\n\n"
            f"Choose an action:"
        )

        await query.edit_message_text(
            details_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    except RuntimeError as e:
        logger.error("Error showing refund details: %s", str(e))
        await query.edit_message_text("❌ Error loading refund details.")


async def process_refund_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process refund approval/denial"""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ Access denied.")
        return

    await query.answer()

    try:
        if not query.data:
            await query.edit_message_text("❌ Invalid request data.")
            return

        action, order_id = query.data.split('_')[0], '_'.join(
            query.data.split('_')[2:])  # Keep order_id as string
        order = db.get_order(order_id)

        if not order:
            await query.edit_message_text("❌ Order not found.")
            return

        if action == "approve":
            # Process wallet refund first
            if wallet_system:
                refund_success = wallet_system.process_refund(
                    user_id=order['user_id'],
                    refund_amount=order['cost'],
                    order_id=order_id,
                    reason="Admin approved refund"
                )

                if not refund_success:
                    await query.edit_message_text(
                        f"❌ <b>Wallet Refund Failed</b>\n\n"
                        f"Failed to process wallet refund for order #{order_id}.\n"
                        f"Please try again or contact system administrator.",
                        parse_mode='HTML'
                    )
                    return

            # Cancel order with SMS Bot if sms_api is available
            if sms_api:
                cancel_result = await sms_api.cancel_order(str(order_id))

                if cancel_result.get('success'):
                    # Update order and refund status
                    db.update_order_status(order_id, 'refunded')
                    db.update_refund_status(order_id, 'approved', user_id)

                    # Notify user with wallet balance update
                    try:
                        user_balance = wallet_system.get_user_balance(
                            order['user_id']) if wallet_system else 0
                        await context.bot.send_message(
                            chat_id=order['user_id'],
                            text=(
                                f"✅ <b>Refund Approved & Processed</b>\n\n"
                                f"Order: #{order_id}\n"
                                f"💰 Refund Amount: ${order['cost']}\n"
                                f"📞 Number: {order['number']}\n"
                                f"💰 New Balance: ${user_balance:.2f}\n\n"
                                f"✅ Order cancelled with provider\n"
                                f"✅ Amount refunded to your wallet"
                            ),
                            parse_mode='HTML'
                        )
                    except RuntimeError as e:
                        logger.error(
                            "Failed to notify user %s: %s", order['user_id'], str(e))

                    await query.edit_message_text(
                        f"✅ <b>Refund Approved & Processed</b>\n\n"
                        f"Order #{order_id} refund completed:\n"
                        f"💰 ${order['cost']} refunded to wallet\n"
                        f"📞 Order cancelled with provider\n"
                        f"👤 User {order['user_id']} notified",
                        parse_mode='HTML'
                    )

                    logger.info(
                        "✅ Refund approved and wallet credited by admin %s for order %s", user_id, order_id)
                else:
                    await query.edit_message_text(
                        f"⚠️ <b>Partial Refund Success</b>\n\n"
                        f"💰 Wallet refunded: ${order['cost']}\n"
                        f"❌ Provider cancellation failed: {cancel_result.get('message', 'Unknown error')}\n\n"
                        f"User has been refunded to wallet.",
                        parse_mode='HTML'
                    )
            else:
                # SMS API not available, but still approve the refund with wallet
                db.update_order_status(order_id, 'refunded')
                db.update_refund_status(order_id, 'approved', user_id)

                # Notify user about wallet refund
                try:
                    user_balance = wallet_system.get_user_balance(
                        order['user_id']) if wallet_system else 0
                    await context.bot.send_message(
                        chat_id=order['user_id'],
                        text=(
                            f"✅ <b>Refund Approved & Processed</b>\n\n"
                            f"Order: #{order_id}\n"
                            f"💰 Refund Amount: ${order['cost']}\n"
                            f"📞 Number: {order['number']}\n"
                            f"💰 New Balance: ${user_balance:.2f}\n\n"
                            f"✅ Amount refunded to your wallet"
                        ),
                        parse_mode='HTML'
                    )
                except RuntimeError as e:
                    logger.error("Failed to notify user %s: %s",
                                 order['user_id'], str(e))

                await query.edit_message_text(
                    f"✅ <b>Refund Approved & Processed</b>\n\n"
                    f"Order #{order_id} refund completed:\n"
                    f"💰 ${order['cost']} refunded to wallet\n"
                    f"👤 User {order['user_id']} notified\n"
                    f"ℹ️ Provider cancellation not available",
                    parse_mode='HTML'
                )

        elif action == "deny":
            # Update refund status
            db.update_refund_status(order_id, 'denied', user_id)

            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=order['user_id'],
                    text=(
                        f"❌ <b>Refund Denied</b>\n\n"
                        f"Your refund request for order #{order_id} has been denied.\n"
                        f"📞 Number: {order['number']}\n\n"
                        f"If you believe this is an error, please contact support."
                    ),
                    parse_mode='HTML'
                )
            except RuntimeError as e:
                logger.error(
                    "Failed to notify user %s: %s", order['user_id'], str(e))

            await query.edit_message_text(
                f"❌ <b>Refund Denied</b>\n\n"
                f"Order #{order_id} refund has been denied.\n"
                f"User {order['user_id']} has been notified.",
                parse_mode='HTML'
            )

            logger.info(
                "❌ Refund denied by admin %s for order %s", user_id, order_id)

    except RuntimeError as e:
        logger.error("Error processing refund action: %s", str(e))
        await query.edit_message_text("❌ Error processing refund action.")

# =============================================================================
# WALLET-BASED PURCHASE HANDLERS (Payment system removed)
# =============================================================================

# REMOVED: handle_wallet_purchase_confirmation - now auto-processed
# REMOVED: handle_confirm_cancel - now auto-processed
# REMOVED: handle_keep_order - no longer needed

# Old payment handlers removed - now using wallet system only
# All service purchases are now instant using wallet balance
# Admin approval only needed for deposits, not individual purchases


async def handle_payment_sent_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user claims payment is sent"""
    query = update.callback_query
    if not query or not query.from_user:
        return

    # Extract payment ID from callback data: "payment_sent_PAY_7396254803_1754854768"
    if not query.data:
        await query.answer("❌ Invalid request.")
        return

    # Get "PAY_7396254803_1754854768"
    payment_id = "_".join(query.data.split('_')[2:])
    user = query.from_user

    await query.answer()

    # Notify all admins about payment claim
    for admin_id in ADMIN_IDS:
        try:
            keyboard = [[
                InlineKeyboardButton(
                    "✅ Approve", callback_data=f"approve_payment_{payment_id}"),
                InlineKeyboardButton(
                    "❌ Deny", callback_data=f"deny_payment_{payment_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            username = user.username or "Unknown"
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"💰 <b>Payment Claim Received</b>\n\n"
                    f"👤 <b>User:</b> {user.id} (@{username})\n"
                    f"💰 <b>Amount:</b> $5.00 (minimum deposit)\n"
                    f"🆔 <b>Payment ID:</b> <code>{payment_id}</code>\n"
                    f"🏦 <b>Wallet:</b> <code>{BINANCE_WALLET}</code>\n\n"
                    f"⚠️ <b>Please verify the payment before approving!</b>"
                ),
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        except RuntimeError as e:
            logger.error("Failed to notify admin %s: %s", admin_id, str(e))

    await query.edit_message_text(
        f"✅ <b>Payment Claim Submitted</b>\n\n"
        f"🆔 <b>Payment ID:</b> <code>{payment_id}</code>\n\n"
        f"👨‍💼 Admins have been notified and will verify your payment.\n"
        f"⏰ You'll be notified once the payment is approved.\n\n"
        f"💡 <b>Note:</b> Only send the exact amount to avoid delays.",
        parse_mode='HTML'
    )

    logger.info("💰 Payment claim submitted by user %s: %s",
                user.id if user else 'Unknown', payment_id)


async def handle_cancel_payment(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle payment cancellation"""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    await query.edit_message_text(
        "❌ <b>Payment Cancelled</b>\n\n"
        "You can start the purchase process again anytime using /buy or the menu.",
        parse_mode='HTML'
    )

    user_id = query.from_user.id if query.from_user else "Unknown"
    logger.info("💰 Payment cancelled by user %s", user_id)


# =============================================================================
# ORDER MANAGEMENT & CANCELLATION HANDLERS
# =============================================================================


async def process_order_cancellation(user_id: int, order_id: str, order: Dict, query):
    """Process order cancellation immediately without confirmation"""
    try:
        # Cancel the polling task if it's active
        if order_id in active_polls:
            active_polls[order_id].cancel()
            del active_polls[order_id]
            logger.info("🛑 Cancelled active polling for order %s", order_id)

        # Cancel the order in SMSPool API
        api_cancel_success = False
        api_cancelled_via_api = False
        api_message = "API not available"

        if sms_api:
            try:
                cancel_result = await sms_api.cancel_order(str(order_id))
                api_cancel_success = cancel_result.get('success', False)
                api_cancelled_via_api = cancel_result.get(
                    'cancelled_via_api', False)
                api_message = cancel_result.get(
                    'message', 'Unknown API response')

                if api_cancel_success:
                    logger.info(
                        "✅ Successfully cancelled order %s via SMSPool API", order_id)
                else:
                    logger.warning(
                        "⚠️ Failed to cancel order %s via SMSPool API: %s", order_id, api_message)
            except Exception as api_error:
                logger.error(
                    "❌ Error cancelling order %s via API: %s", order_id, api_error)
                api_message = f"API error: {str(api_error)}"

        # Process reservation cancellation via wallet system (no refund needed since no charge occurred)
        cancel_success = False
        if wallet_system:
            reservation_order_id = order.get('reservation_order_id')
            service_cost = order.get('cost', 0)

            if reservation_order_id:
                # Cancel the reservation since order is being cancelled
                cancel_success = wallet_system.cancel_reservation(
                    user_id=user_id,
                    amount=service_cost,
                    order_id=str(order_id),
                    reason="User cancelled order"
                )

                if cancel_success:
                    logger.info(
                        "🚫 RESERVATION CANCELLED: User %s cancelled order %s - no charge occurred",
                        user_id, order_id)
                else:
                    logger.warning(
                        "⚠️ Failed to cancel reservation for order %s - continuing with cancellation",
                        order_id)
            else:
                # No reservation found, may be old order - try to refund if already charged
                refund_success = wallet_system.process_refund(
                    user_id=user_id,
                    refund_amount=order['cost'],
                    order_id=str(order_id),
                    reason="User cancelled order - legacy refund"
                )
                cancel_success = refund_success
                if refund_success:
                    logger.info(
                        "💰 LEGACY REFUND: Processed refund for old order %s", order_id)

        # Update order status
        if cancel_success or not wallet_system:
            db.update_order_status(order_id, 'cancelled')
            user_balance = wallet_system.get_user_balance(
                user_id) if wallet_system else 0.00

            await query.edit_message_text(
                f"✅ <b>Order Cancelled Successfully</b>\n\n"
                f"🆔 <b>Order ID:</b> #{order_id}\n"
                f"💰 <b>Good News:</b> No charge to your wallet!\n"
                f"💰 <b>Current Balance:</b> ${user_balance:.2f}\n\n"
                f"✅ Your order has been cancelled successfully.\n"
                f"🔄 <b>API Status:</b> {api_message}\n\n"
                f"💡 You can place a new order anytime or use 'Order Again' for the same service!",
                parse_mode='HTML',
                reply_markup=create_order_again_keyboard(order_id, order)
            )

            logger.info(
                "✅ Order %s cancelled successfully for user %s - no charge occurred", order_id, user_id)
        else:
            await query.edit_message_text(
                f"⚠️ <b>Order Cancelled (Wallet Issue)</b>\n\n"
                f"🆔 <b>Order ID:</b> #{order_id}\n"
                f"🔄 Your order has been cancelled but there was an issue with the wallet system.\n"
                f"💰 Please contact support if you were charged.\n\n"
                f"🔄 <b>API Status:</b> {api_message}",
                parse_mode='HTML'
            )

            logger.error(
                "❌ Order %s cancelled but wallet operation failed for user %s", order_id, user_id)

    except Exception as e:
        logger.error("❌ Error processing order cancellation: %s", str(e))
        await query.edit_message_text(
            f"❌ <b>Cancellation Error</b>\n\n"
            f"An error occurred while cancelling your order.\n"
            f"Please try again or contact support.",
            parse_mode='HTML'
        )


async def handle_cancel_order(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle order cancellation request from user"""
    query = update.callback_query
    if not query or not query.from_user or not query.data:
        return

    user_id = query.from_user.id
    await query.answer()

    try:
        # Extract order_id from callback data: "cancel_order_{order_id}"
        order_id = "_".join(query.data.split('_')[2:])  # Keep as string

        # Verify order exists and belongs to user
        order = db.get_order(order_id)
        if not order:
            await query.edit_message_text(
                "❌ <b>Order Not Found</b>\n\n"
                "This order could not be found or may have been already processed.",
                parse_mode='HTML'
            )
            return

        if order['user_id'] != user_id:
            await query.edit_message_text(
                "❌ <b>Access Denied</b>\n\n"
                "You can only cancel your own orders.",
                parse_mode='HTML'
            )
            return

        # Check if order can be cancelled (must be pending and no OTP received)
        if order['status'] not in ['pending']:
            status_messages = {
                'completed': 'This order has already been completed with OTP delivery.',
                'cancelled': 'This order has already been cancelled.',
                'timeout': 'This order has already timed out.',
                'refunded': 'This order has already been refunded.',
                'error': 'This order has already been marked as error.'
            }

            message = status_messages.get(
                order['status'], f"This order has status: {order['status']}")

            await query.edit_message_text(
                f"❌ <b>Cannot Cancel Order</b>\n\n"
                f"🆔 <b>Order:</b> #{order_id}\n"
                f"🔄 <b>Status:</b> {order['status']}\n\n"
                f"📝 <b>Reason:</b> {message}\n\n"
                f"💡 If you believe this is an error, contact an administrator.",
                parse_mode='HTML'
            )
            return

        # AUTO-PROCESS cancellation immediately without confirmation
        number = order.get('number', 'N/A')
        cost = order.get('cost', 'N/A')

        await query.edit_message_text(
            f"🔄 <b>Cancelling Order...</b>\n\n"
            f"🆔 <b>Order ID:</b> #{order_id}\n"
            f"📱 <b>Number:</b> <code>{number}</code>\n"
            f"💰 <b>Amount:</b> ${cost}\n\n"
            f"⚡ <b>Processing automatic cancellation...</b>\n"
            f"💰 Good news: No charge will be made to your wallet!\n"
            f"🔄 OTP monitoring will stop",
            parse_mode='HTML'
        )

        # Process cancellation immediately
        await process_order_cancellation(user_id, order_id, order, query)

        logger.info(
            "⚡ Auto-processed cancellation for order %s by user %s", order_id, user_id)

    except RuntimeError as e:
        logger.error("❌ Error in cancel order handler: %s", str(e))
        await query.edit_message_text(
            "❌ <b>Error</b>\n\n"
            "An error occurred while processing your cancellation request.\n"
            "Please try again or contact support.",
            parse_mode='HTML'
        )

# REMOVED: handle_confirm_cancel - now auto-processed
# REMOVED: handle_keep_order - no longer needed with auto-processing


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data

    try:
        # NEW: Enhanced menu system callbacks
        if data == "start_menu":
            await handle_start_menu(update, context)
        elif data == "my_orders":
            await handle_my_orders(update, context)
        elif data == "quick_refund":
            await handle_quick_refund(update, context)
        elif data == "show_help":
            await handle_show_help(update, context)
        elif data == "contact_us":
            await handle_contact_us(update, context)
        elif data == "admin_panel":
            await handle_admin_panel(update, context)
        elif data == "service_status":
            await service_status_command(update, context)
        elif data == "pending_deposits":
            await handle_pending_deposits(update, context)
        elif data == "detailed_stats":
            await handle_detailed_stats(update, context)

        # Wallet-related callbacks
        elif data == "deposit_funds":
            await handle_deposit_funds(update, context)
        elif data == "deposit_method_wallet":
            await handle_deposit_method_wallet(update, context)
        elif data == "deposit_method_binance":
            await handle_deposit_method_binance(update, context)
        elif data.startswith("deposit_wallet_"):
            await handle_deposit_wallet_amount(update, context)
        elif data.startswith("deposit_binance_"):
            await handle_deposit_binance_amount(update, context)
        elif data.startswith("deposit_amount_"):
            await handle_deposit_amount(update, context)
        elif data.startswith("deposit_sent_"):
            await handle_deposit_sent(update, context)
        elif data.startswith("binance_sent_"):
            await handle_binance_deposit_sent(update, context)
        elif data == "cancel_deposit":
            await handle_cancel_deposit(update, context)
        elif data == "show_balance":
            await balance_command(update, context)
        elif data == "transaction_history":
            await handle_transaction_history(update, context)

        # Service purchase with wallet - AUTO-PROCESS (no confirmation callbacks needed)
        elif data.startswith("wallet_service_"):
            await handle_service_purchase_with_wallet(update, context)
        elif data.startswith("wallet_purchase_"):
            # Handle direct wallet purchase callbacks (e.g., wallet_purchase_1574_0.15)
            await handle_wallet_purchase_callback(update, context)
        # REMOVED: wallet_purchase_ confirmation - now auto-processed

        # NEW: Service selection and country workflow
        elif data == "browse_services":
            await handle_browse_services(update, context)
        elif data.startswith("select_service_"):
            await handle_service_selection(update, context)
        elif data.startswith("country_") and len(data.split('_')) >= 4:
            # Handle country selection with service info: country_1_1574_0.17
            await handle_country_selection_with_service(update, context)
        elif data.startswith("instant_purchase_"):
            await handle_instant_purchase(update, context)
        elif data.startswith("all_countries_"):
            await handle_show_all_countries_for_service(update, context)
        elif data.startswith("search_countries_"):
            await handle_country_search_for_service(update, context)

        # Legacy handlers (kept for backward compatibility)
        elif data.startswith("country_"):
            await handle_country_selection(update, context)
        elif data == "all_countries":
            await handle_show_all_countries(update, context)
        elif data == "search_countries":
            await handle_country_search(update, context)
        elif data.startswith("service_"):
            await handle_service_selection_with_country(update, context)

        # Legacy service selection (kept for backward compatibility)
        elif data.startswith("select_service_"):
            await handle_service_selection(update, context)
        elif data == "back_to_start" or data == "start":
            await handle_start_menu(update, context)

        # Legacy Ring4 workflow (kept for backward compatibility)
        elif data == "buy_ring4":
            await handle_buy_ring4(update, context)

        # OLD PAYMENT SYSTEM REMOVED - Now using wallet system only
        # All service purchases are instant using wallet balance
        # Admin approval only needed for deposits, not individual purchases

        # Refund workflow callbacks (now automatic - no admin approval needed)
        elif data.startswith("instant_refund_reorder_"):
            await handle_instant_refund_and_reorder(update, context)
        elif data.startswith("refund_reorder_"):
            await handle_refund_and_reorder(update, context)
        elif data.startswith("refund_") and not data.startswith("refund_details_"):
            await handle_refund_request(update, context)

        # Order Again callbacks - Allow users to reorder same service/country
        elif data.startswith("order_again_"):
            await handle_order_again(update, context)

        # Order cancellation callbacks - AUTO-PROCESS (no confirmation callbacks needed)
        elif data.startswith("cancel_order_"):
            await handle_cancel_order(update, context)
        # REMOVED: confirm_cancel_ and keep_order_ - now auto-processed

        # Admin deposit management
        elif data.startswith("approve_deposit_"):
            await handle_approve_deposit(update, context)
        elif data.startswith("deny_deposit_"):
            await handle_deny_deposit(update, context)

        elif data == "deposit_custom":
            # Handle custom deposit amount
            await handle_deposit_custom(update, context)
        elif data == "deposit_wallet_custom":
            # Handle custom wallet deposit
            await handle_deposit_wallet_custom(update, context)
        elif data == "deposit_binance_custom":
            # Handle custom Binance deposit
            await handle_deposit_binance_custom(update, context)

        # Unknown callback
        else:
            await query.answer("❌ Unknown action.")
            logger.warning("Unknown callback data: %s", data)

    except Exception as e:
        # Handle both RuntimeError and other exceptions like BadRequest
        error_msg = str(e)

        # Special handling for BadRequest (message not modified)
        if "Message is not modified" in error_msg:
            logger.warning(
                "Message not modified error - likely duplicate content: %s", error_msg)
            try:
                await query.answer("✅ Action completed.")
            except Exception:
                pass
            return
        elif "message to edit not found" in error_msg.lower():
            logger.warning(
                "Message to edit not found - user may have deleted it: %s", error_msg)
            try:
                await query.answer("❌ Message no longer available.")
            except Exception:
                pass
            return
        elif "message is not modified" in error_msg.lower():
            logger.warning("Duplicate message content detected: %s", error_msg)
            try:
                await query.answer("✅ No changes needed.")
            except Exception:
                pass
            return
        else:
            logger.error("Error in callback query handler: %s", error_msg)
            try:
                await query.answer("❌ An error occurred.")
                # Try to send a simple error message to the chat
                if update.effective_chat:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ <b>Error</b>\n\n"
                             "An error occurred processing your request. Please try again.",
                        parse_mode='HTML'
                    )
            except Exception as inner_e:
                logger.error("Failed to send error message: %s", inner_e)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (for custom deposit amounts and country search)"""
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    message = update.message
    text = message.text

    if not text:
        return

    # Check if user is searching for countries
    if context.user_data and context.user_data.get('awaiting_country_search'):
        try:
            search_term = text.strip()

            if len(search_term) < 2:
                await message.reply_text(
                    "🔍 <b>Search too short!</b>\n\n"
                    "Please enter at least 2 characters to search for countries.",
                    parse_mode='HTML'
                )
                return

            # Clear the search state
            context.user_data['awaiting_country_search'] = False

            # Search for countries
            matching_countries = sms_api.search_countries(
                search_term) if sms_api else []

            if not matching_countries:
                await message.reply_text(
                    f"🔍 <b>No countries found for '{search_term}'</b>\n\n"
                    "Try searching with a different term.",
                    parse_mode='HTML'
                )
                return

            # Show search results
            keyboard = []
            for country in matching_countries[:15]:  # Limit to 15 results
                keyboard.append([InlineKeyboardButton(
                    f"{country['flag']} {country['name']}",
                    callback_data=f"country_{country['id']}"
                )])

            # Add back button
            keyboard.append([InlineKeyboardButton(
                "🔙 Back to Countries", callback_data="browse_services")])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await message.reply_text(
                f"🔍 <b>Search Results for '{search_term}':</b>\n\n"
                f"Found {len(matching_countries)} countries",
                parse_mode='HTML',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error("Error handling country search: %s", e)
            await message.reply_text(
                "❌ Error searching for countries. Please try again.",
                parse_mode='HTML'
            )
            context.user_data['awaiting_country_search'] = False
        return

    # Check if user is entering a custom deposit amount
    if context.user_data and context.user_data.get('awaiting_deposit_amount'):
        try:
            # Parse the amount
            amount = float(text.strip())

            # Validate amount
            min_amount = wallet_system.MIN_DEPOSIT_USD if wallet_system else 5.00
            max_amount = wallet_system.MAX_DEPOSIT_USD if wallet_system else 1000.00

            if amount < min_amount:
                await message.reply_text(
                    f"❌ <b>Amount too low!</b>\n\n"
                    f"Minimum deposit: ${min_amount:.2f}\n"
                    f"Please try again.",
                    parse_mode='HTML'
                )
                return

            if amount > max_amount:
                await message.reply_text(
                    f"❌ <b>Amount too high!</b>\n\n"
                    f"Maximum deposit: ${max_amount:.2f}\n"
                    f"Please try again.",
                    parse_mode='HTML'
                )
                return

            # Get deposit method from user context
            deposit_method = context.user_data.get('deposit_method', 'wallet')

            # Clear the state
            context.user_data['awaiting_deposit_amount'] = False
            context.user_data.pop('deposit_method', None)

            # Create deposit request based on method
            if wallet_system:
                if deposit_method == 'binance':
                    # Create Binance deposit request
                    if not BINANCE_ID:
                        await message.reply_text(
                            "❌ <b>Binance ID Not Configured</b>\n\n"
                            "Please contact administrator to set up Binance transfers.",
                            parse_mode='HTML'
                        )
                        return

                    deposit_request = wallet_system.create_binance_deposit_request(
                        user_id=user.id,
                        amount=amount,
                        binance_id=BINANCE_ID
                    )

                    # Format Binance deposit instructions
                    instructions_text = (
                        f"🟡 <b>Binance Transfer Instructions</b>\n\n"
                        f"💰 <b>Amount:</b> ${amount:.2f} USDT\n\n"
                        f"Please make the payment via Binance (Binance to Binance transfer) to minimize transaction fees.\n\n"
                        f"🆔 <b>My Binance ID:</b> <code>{BINANCE_ID}</code>\n\n"
                        f"📋 <b>Instructions:</b>\n"
                        f"1. Open Binance app/website\n"
                        f"2. Go to Pay → Transfer\n"
                        f"3. Enter Binance ID: <code>{BINANCE_ID}</code>\n"
                        f"4. Send exactly <b>${amount:.2f} USDT</b>\n"
                        f"5. Copy the Transaction ID (TXID)\n"
                        f"6. Click 'Payment Sent' below\n\n"
                        f"⚠️ <b>Important:</b>\n"
                        f"• Send exactly the specified amount\n"
                        f"• Use USDT (Tether USD)\n"
                        f"• Save your transaction receipt\n\n"
                        f"After payment, please enter your Transaction ID (TXID) or upload a screenshot.\n"
                        f"Once admin verifies, your balance will be credited.\n\n"
                        f"🆔 <b>Deposit ID:</b> <code>{deposit_request['deposit_id']}</code>"
                    )

                    keyboard = [[
                        InlineKeyboardButton(
                            "✅ Payment Sent", callback_data=f"binance_sent_{deposit_request['deposit_id']}"),
                        InlineKeyboardButton(
                            "❌ Cancel", callback_data="cancel_deposit")
                    ]]

                else:
                    # Create wallet deposit request (default)
                    deposit_request = wallet_system.create_deposit_request(
                        user_id=user.id,
                        amount=amount,
                        binance_wallet=BINANCE_WALLET
                    )

                    # Format wallet deposit instructions
                    instructions_text = "� <b>Wallet Deposit Request</b>\n\n"
                    instructions_text += "\n".join(
                        deposit_request['instructions'])

                    keyboard = [[
                        InlineKeyboardButton(
                            "✅ Payment Sent", callback_data=f"deposit_sent_{deposit_request['deposit_id']}"),
                        InlineKeyboardButton(
                            "❌ Cancel", callback_data="cancel_deposit")
                    ]]

                reply_markup = InlineKeyboardMarkup(keyboard)

                await message.reply_text(
                    instructions_text,
                    parse_mode='HTML' if deposit_method == 'binance' else 'Markdown',
                    reply_markup=reply_markup
                )

                logger.info(
                    "💰 Custom %s deposit request created for user %s: $%.2f",
                    deposit_method, user.id, amount)
            else:
                await message.reply_text("❌ Wallet system not available.")

        except ValueError:
            await message.reply_text(
                "❌ <b>Invalid amount format!</b>\n\n"
                "Please enter a valid number (e.g., 10.50)\n"
                "No symbols like $ or USD needed.",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error("Error handling custom deposit amount: %s", e)
            await message.reply_text(
                "❌ Error processing your deposit amount. Please try again."
            )
            context.user_data['awaiting_deposit_amount'] = False
            context.user_data.pop('deposit_method', None)

# =============================================================================
# ERROR HANDLING
# =============================================================================


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    # Get traceback
    if context.error:
        tb_list = traceback.format_exception(
            None, context.error, context.error.__traceback__)
        logger.error("Error traceback: %s", "".join(tb_list))
    else:
        logger.error("No error traceback available")

    # Notify admins about the error (optional)
    if ADMIN_IDS and update:
        try:
            error_message = str(
                context.error) if context.error else "Unknown error"
            # Only notify first admin to avoid spam
            for admin_id in ADMIN_IDS[:1]:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"⚠️ <b>Bot Error</b>\n\n<code>{error_message[:500]}</code>",
                    parse_mode='HTML'
                )
        except OSError:
            pass

# =============================================================================
# PROCESS MANAGEMENT TO PREVENT MULTIPLE INSTANCES
# =============================================================================


def check_and_create_pidfile():
    """Check if bot is already running and create PID file"""
    pid_file = LOGS_DIR / "ring4_bot.pid"

    if pid_file.exists():
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())

            # Check if process is still running
            try:
                os.kill(old_pid, 0)  # Send signal 0 to check if process exists
                logger.error("❌ Bot is already running with PID %d", old_pid)
                logger.error(
                    "💡 Stop the existing bot first or wait for it to finish")
                sys.exit(1)
            except OSError:
                # Process doesn't exist, remove stale PID file
                logger.warning(
                    "🧹 Removing stale PID file for process %d", old_pid)
                pid_file.unlink()
        except (ValueError, IOError) as e:
            logger.warning("⚠️ Invalid PID file, removing: %s", e)
            try:
                pid_file.unlink()
            except OSError:
                pass

    # Create new PID file
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        logger.info("✅ Created PID file: %s (PID: %d)", pid_file, os.getpid())
        return pid_file
    except IOError as e:
        logger.error("❌ Failed to create PID file: %s", e)
        return None


def cleanup_pidfile(pid_file):
    """Clean up PID file on exit"""
    if pid_file and pid_file.exists():
        try:
            pid_file.unlink()
            logger.info("🧹 Cleaned up PID file")
        except OSError as e:
            logger.warning("⚠️ Failed to clean up PID file: %s", e)


def signal_handler(signum, frame, pid_file=None):
    """Handle shutdown signals gracefully"""
    logger.info("🛑 Received signal %d, shutting down gracefully...", signum)
    cleanup_pidfile(pid_file)
    sys.exit(0)


# =============================================================================
# APPLICATION SETUP & MAIN
# =============================================================================


def validate_environment():
    """Validate required environment variables"""
    if not BOT_TOKEN:
        logger.critical("❌ BOT_TOKEN not found in environment")
        return False

    if not SMSPOOL_API_KEY:
        logger.critical("❌ SMSPOOL_API_KEY not found in environment")
        return False

    if not ADMIN_IDS:
        logger.warning("⚠️ No ADMIN_IDS configured - admin features disabled")

    logger.info("✅ Environment validation passed")
    return True


def main():
    """Main entry point with process management"""
    logger.info("🚀 Starting Ring4 US-Only SMS Verification Bot")
    logger.info("🐍 Python version: %s", sys.version)
    logger.info("📁 Working directory: %s", os.getcwd())

    # Check for existing bot instances and create PID file
    pid_file = check_and_create_pidfile()

    # Set up signal handlers for graceful shutdown
    def signal_handler_wrapper(signum, frame):
        signal_handler(signum, frame, pid_file)

    signal.signal(signal.SIGINT, signal_handler_wrapper)
    signal.signal(signal.SIGTERM, signal_handler_wrapper)

    # Print startup banner
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║              📱 RING4 SMS VERIFICATION BOT                   ║
    ║                                                              ║
    ║                   Production Ready v2.0                      ║
    ║                                                              ║
    ║  🎯 Core Features:                                           ║
    ║    • Ring4 US numbers only (Service ID: 1574)                ║
    ║    • Instant purchase & delivery                            ║
    ║    • Real-time OTP polling (adaptive intervals)             ║
    ║    • 10-minute validity period                              ║
    ║    • ⚡ INSTANT automatic refunds                           ║
    ║    • Persistent TinyDB storage                              ║
    ║    • Production error handling                               ║
    ║                                                              ║
    ║  🚀 NEW: Enhanced UX Features:                              ║
    ║    • 📱 Persistent menu system                              ║
    ║    • 🔄 Quick action buttons                                ║
    ║    • 📋 One-click order history                             ║
    ║    • 💸 Instant refund system                               ║
    ║    • ❔ Built-in help & guidance                            ║
    ║    • 👨‍💼 Admin quick panel                                  ║
    ║                                                              ║
    ║  💰 Business Ready:                                          ║
    ║    • SMSPool API integration                                ║
    ║    • Automated refund processing                            ║
    ║    • Full audit trails & logging                           ║
    ║    • Async-first implementation                             ║
    ║                                                              ║
    ║  ⚡ Instant Everything:                                      ║
    ║    • No admin approval for refunds                          ║
    ║    • No purchase confirmations                              ║
    ║    • Menu-driven navigation                                 ║
    ║    • Mobile-optimized interface                             ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    try:
        # Validate environment
        if not validate_environment():
            cleanup_pidfile(pid_file)
            sys.exit(1)

        # Create application with conflict resolution
        if not BOT_TOKEN:
            logger.critical("❌ BOT_TOKEN not configured")
            cleanup_pidfile(pid_file)
            sys.exit(1)

        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .concurrent_updates(True)  # Enable concurrent updates
            .build()
        )

        # Setup persistent bot menu system
        async def post_init(app: Application) -> None:
            """Post-initialization tasks"""
            await setup_bot_menu(app)
            logger.info("🎯 Bot menu system initialized")

        # Run menu setup after bot initialization
        application.post_init = post_init

        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("buy", buy_command))
        application.add_handler(CommandHandler("services", services_command))
        application.add_handler(CommandHandler("deposit", deposit_command))
        application.add_handler(CommandHandler("balance", balance_command))
        application.add_handler(CommandHandler("orders", orders_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("contact", contact_command))
        application.add_handler(CommandHandler("refund", refund_command))
        application.add_handler(CommandHandler("admin", admin_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler(
            "approve_refund", approve_refund_command))

        # Add database admin commands
        try:
            from src.database_admin import DatabaseAdminCommands
            db_admin = DatabaseAdminCommands(db)

            application.add_handler(CommandHandler(
                "db_status", db_admin.protection_status))
            application.add_handler(CommandHandler(
                "db_backups", db_admin.list_backups))
            application.add_handler(CommandHandler(
                "db_backup", db_admin.manual_backup))
            application.add_handler(CommandHandler(
                "db_validate", db_admin.validate_database))
            application.add_handler(CommandHandler(
                "db_emergency", db_admin.create_emergency_backup))

            logger.info("✅ Database admin commands registered")

        except ImportError as e:
            logger.warning(f"⚠️ Database admin commands not available: {e}")

        # Add callback query handler
        application.add_handler(CallbackQueryHandler(callback_query_handler))

        # Add message handler for custom deposit amounts
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, handle_text_message))

        # Add error handler
        application.add_error_handler(error_handler)

        logger.info("✅ Application setup complete")
        logger.info("🤖 Starting bot polling...")

        try:
            # Start the bot with improved polling configuration
            # The webhook will be cleared automatically by drop_pending_updates=True
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,  # This automatically clears webhooks
                timeout=20,  # Increase timeout to handle network issues
            )
        except Exception as polling_error:
            if "Conflict" in str(polling_error) and "getUpdates" in str(polling_error):
                logger.error(
                    "🚨 Another bot instance is running. Error: %s", polling_error)
                logger.error(
                    "💡 Solution: Stop any other bot instances or clear webhooks")
                logger.error("💡 Commands to try:")
                logger.error("   - pkill -f 'python.*main.py'")
                logger.error("   - Check Telegram webhook settings")
                logger.error("   - Wait a few seconds and restart")
                logger.error("💡 PID file location: %s",
                             pid_file if pid_file else "Not created")
            else:
                logger.error("❌ Polling error: %s", polling_error)
            raise

    except KeyboardInterrupt:
        logger.info("⌨️ Bot stopped by user")
    except Exception as e:
        logger.critical("💥 Fatal error: %s", str(e), exc_info=True)
        cleanup_pidfile(pid_file)
        sys.exit(1)
    finally:
        # Clean up active polling tasks before event loop closes
        try:
            if active_polls:
                logger.info(
                    "🧹 Cleaning up %s active polling tasks...", len(active_polls))
                for order_id, task in list(active_polls.items()):
                    if not task.cancelled():
                        task.cancel()
                        logger.debug(
                            "❌ Cancelled polling task for order %s", order_id)
                active_polls.clear()
                logger.info("✅ All polling tasks cleaned up")
        except Exception as cleanup_error:
            logger.error("⚠️ Error during cleanup: %s", cleanup_error)

        # Close database connections safely
        try:
            if 'db' in globals() and db:
                db.close()
        except Exception as db_error:
            logger.error("⚠️ Error closing database: %s", db_error)

        # Clean up PID file
        cleanup_pidfile(pid_file)
        logger.info("👋 Ring4 Bot shutdown complete")


if __name__ == "__main__":
    main()
