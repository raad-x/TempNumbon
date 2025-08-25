"""
Advanced Configuration Manager for Ring4 SMS Bot
Centralized configuration system with validation and hot-reload capabilities
"""
import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Advanced Configuration Manager for Ring4 SMS Bot

    Features:
    - Centralized configuration from config.env
    - Fallback to .env and environment variables
    - Type validation and conversion
    - Service management and prioritization
    - Hot-reload capabilities
    - Non-technical user friendly
    """

    _instance = None
    _config_cache = {}
    _last_reload = None

    # Default configuration values
    DEFAULTS = {
        # Core
        'BOT_TOKEN': '',
        'SMSPOOL_API_KEY': '',
        'ADMIN_IDS': '',
        'BINANCE_WALLET': '',
        'BINANCE_ID': '',
        'CONTACT_ACCOUNT_1': '',
        'CONTACT_ACCOUNT_2': '',

        # Services
        'ENABLE_RING4': True,
        'ENABLE_TELEGRAM': True,
        'ENABLE_GOOGLE': True,
        'ENABLE_WHATSAPP': True,
        'RING4_SERVICE_ID': 1574,
        'TELEGRAM_SERVICE_ID': 22,
        'GOOGLE_SERVICE_ID': 395,
        'WHATSAPP_SERVICE_ID': 1012,
        'RING4_PRIORITY': 1,
        'TELEGRAM_PRIORITY': 2,
        'GOOGLE_PRIORITY': 3,
        'WHATSAPP_PRIORITY': 4,
        'RING4_DISPLAY_NAME': 'Ring4',
        'TELEGRAM_DISPLAY_NAME': 'Telegram',
        'GOOGLE_DISPLAY_NAME': 'Google/Gmail',
        'WHATSAPP_DISPLAY_NAME': 'WhatsApp',
        'RING4_DESCRIPTION': 'Ring4 US numbers (recommended)',
        'TELEGRAM_DESCRIPTION': 'Telegram US numbers',
        'GOOGLE_DESCRIPTION': 'Google/Gmail US numbers',
        'WHATSAPP_DESCRIPTION': 'WhatsApp US numbers',

        # Pricing
        'PROFIT_MARGIN_PERCENT': 5.0,
        'MIN_PRICE_USD': 0.15,
        'MAX_PRICE_USD': 1.00,
        'USE_FIXED_PRICING': False,
        'RING4_FIXED_PRICE': 0.17,
        'TELEGRAM_FIXED_PRICE': 0.25,
        'GOOGLE_FIXED_PRICE': 0.42,
        'WHATSAPP_FIXED_PRICE': 0.35,
        'RING4_PROFIT_MARGIN': '',
        'TELEGRAM_PROFIT_MARGIN': '',
        'GOOGLE_PROFIT_MARGIN': '',
        'WHATSAPP_PROFIT_MARGIN': '',

        # Wallet
        'MIN_DEPOSIT_USD': 1.00,
        'MAX_DEPOSIT_USD': 1000.00,
        'AUTO_APPROVE_BELOW_USD': 0.00,
        'ENABLE_WALLET_SYSTEM': True,

        # Polling
        'POLL_INTERVAL': 2,
        'POLL_TIMEOUT': 600,
        'ORDER_EXPIRES_IN': 600,
        'POLLING_INITIAL_INTERVAL': 2,
        'POLLING_ACTIVE_INTERVAL': 3,
        'POLLING_STANDARD_INTERVAL': 5,
        'POLLING_EXTENDED_INTERVAL': 10,
        'MAX_CONSECUTIVE_FAILURES': 3,
        'API_TIMEOUT_SECONDS': 10,
        'MAX_POLLING_INTERVAL': 30,

        # UI
        'BOT_TITLE': 'Ring4 SMS Verification Bot',
        'BOT_SUBTITLE': 'US Phone Numbers for Verification',
        'LOW_BALANCE_WARNING': 0.15,
        'SHOW_PRICING_IN_MENU': True,
        'SHOW_PROFIT_TO_ADMINS': True,
        'DEFAULT_COUNTRY_ID': 1,
        'DEFAULT_COUNTRY_NAME': 'United States',

        # Business Rules
        'AUTO_REFUND_TIMEOUT': True,
        'AUTO_REFUND_ERRORS': True,
        'MAX_ORDERS_PER_USER_PER_DAY': 10,
        'MAX_ORDERS_PER_USER_PER_HOUR': 3,
        'ENABLE_SERVICE_MONITORING': True,
        'SERVICE_CHECK_INTERVAL': 300,

        # Notifications
        'NOTIFY_ADMINS_NEW_ORDERS': False,
        'NOTIFY_ADMINS_FAILED_ORDERS': True,
        'NOTIFY_ADMINS_DEPOSITS': True,
        'NOTIFY_ADMINS_REFUNDS': True,
        'SEND_DAILY_REPORTS': True,
        'DAILY_REPORT_TIME': '09:00',

        # Technical
        'ENVIRONMENT': 'production',
        'LOG_LEVEL': 'INFO',
        'DATABASE_PATH': 'data/ring4_database.json',
        'ALLOW_MOCK': False,
        'DATABASE_BACKUP_INTERVAL': 24,
        'MAX_LOG_FILE_SIZE': 100,
        'LOG_FILES_TO_KEEP': 7,

        # Security
        'RATE_LIMIT_PER_MINUTE': 10,
        'AUTO_BLOCK_SUSPICIOUS': False,
        'REQUIRE_VERIFICATION_FOR_LARGE_DEPOSITS': True,
        'LARGE_DEPOSIT_THRESHOLD': 100.00,
        'ENABLE_IP_LOGGING': False,

        # Maintenance
        'MAINTENANCE_MODE': False,
        'MAINTENANCE_MESSAGE': 'Bot is currently under maintenance. Please try again later.',
        'ENABLE_PERFORMANCE_MONITORING': True,
        'PERFORMANCE_ALERT_THRESHOLD': 5.0,
        'AUTO_OPTIMIZE_DATABASE': True,
        'DATABASE_OPTIMIZATION_INTERVAL': 168,

        # Features
        'ENABLE_EXPERIMENTAL_FEATURES': False,
        'ENABLE_BETA_MODE': False,
        'ENABLE_DETAILED_ANALYTICS': True,
        'ENABLE_USER_FEEDBACK': False,
        'ENABLE_REFERRAL_SYSTEM': False,

        # Advanced
        'SERVICE_SELECTION_ALGORITHM': 'weighted',
        'ENABLE_DYNAMIC_PRICING': False,
        'DYNAMIC_PRICING_FACTOR': 10.0,
        'ENABLE_BULK_DISCOUNTS': False,
        'BULK_DISCOUNT_THRESHOLD': 5,
        'BULK_DISCOUNT_PERCENTAGE': 10.0,

        # Regional
        'DEFAULT_TIMEZONE': 'UTC',
        'CURRENCY_SYMBOL': '$',
        'DATE_FORMAT': '%Y-%m-%d %H:%M:%S',
        'ENABLE_MULTI_LANGUAGE': False,
        'DEFAULT_LANGUAGE': 'en',

        # Integration
        'ENABLE_WEBHOOK_MODE': False,
        'WEBHOOK_URL': '',
        'WEBHOOK_SECRET': '',
        'ENABLE_EXTERNAL_APIS': False,
        'EXTERNAL_BALANCE_CHECK_URL': '',
        'EXTERNAL_NOTIFICATION_URL': '',
    }

    def __new__(cls, config_file: Optional[str] = None):
        # For testing purposes, allow different instances with different config files
        if config_file:
            instance = super().__new__(cls)
            return instance

        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_file: Optional[str] = None):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.config_file = config_file or 'config.env'
            self.reload_config()

    def reload_config(self) -> None:
        """Reload configuration from all sources"""
        logger.info("🔄 Reloading configuration from all sources...")

        # Load configuration files in order of priority
        config_files = [
            self.config_file,  # Primary configuration file (can be customized)
            '.env',            # Fallback configuration file
        ]

        self._config_cache = {}

        for config_file in config_files:
            if Path(config_file).exists():
                logger.info(f"📁 Loading config from {config_file}")
                load_dotenv(config_file, override=True)
            else:
                logger.debug(
                    f"📁 Config file {config_file} not found, skipping")

        # Load environment variables
        self._load_environment_variables()

        # Validate configuration
        self._validate_configuration()

        logger.info("✅ Configuration reloaded successfully")

    def _load_environment_variables(self) -> None:
        """Load and parse environment variables"""
        for key, default in self.DEFAULTS.items():
            # Get value from environment with fallbacks
            value = (
                os.getenv(key) or
                # Try without underscores
                os.getenv(key.replace('_', '').upper()) or
                os.getenv(key.lower()) or                   # Try lowercase
                str(default)
            )

            # Type conversion based on default value type
            try:
                if isinstance(default, bool):
                    self._config_cache[key] = self._str_to_bool(value)
                elif isinstance(default, int):
                    self._config_cache[key] = int(
                        float(value)) if value else default
                elif isinstance(default, float):
                    self._config_cache[key] = float(
                        value) if value else default
                elif isinstance(default, list):
                    self._config_cache[key] = self._str_to_list(
                        value) if value else default
                else:
                    self._config_cache[key] = value if value else default
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"⚠️ Invalid value for {key}: {value}, using default: {default}")
                self._config_cache[key] = default

    def _str_to_bool(self, value: str) -> bool:
        """Convert string to boolean"""
        return str(value).lower() in ('true', '1', 'yes', 'on', 'enabled')

    def _str_to_list(self, value: str) -> List[str]:
        """Convert comma-separated string to list"""
        if not value:
            return []
        return [item.strip() for item in value.split(',') if item.strip()]

    def _validate_configuration(self) -> None:
        """Validate critical configuration values"""
        errors = []
        warnings = []

        # Required fields validation
        required_fields = ['BOT_TOKEN', 'SMSPOOL_API_KEY', 'ADMIN_IDS']
        for field in required_fields:
            if not self.get(field):
                errors.append(f"Missing required field: {field}")

        # Admin IDs validation
        admin_ids = self.get_admin_ids()
        if not admin_ids:
            errors.append("At least one admin ID must be configured")

        # Pricing validation
        min_price = self.get('MIN_PRICE_USD')
        max_price = self.get('MAX_PRICE_USD')
        if min_price >= max_price:
            warnings.append(
                f"MIN_PRICE_USD ({min_price}) should be less than MAX_PRICE_USD ({max_price})")

        # Wallet validation
        min_deposit = self.get('MIN_DEPOSIT_USD')
        max_deposit = self.get('MAX_DEPOSIT_USD')
        if min_deposit >= max_deposit:
            warnings.append(
                f"MIN_DEPOSIT_USD ({min_deposit}) should be less than MAX_DEPOSIT_USD ({max_deposit})")

        # Service validation
        enabled_services = self.get_enabled_services()
        if not enabled_services:
            warnings.append("No services are enabled")

        # Log validation results
        if errors:
            for error in errors:
                logger.error(f"❌ Configuration error: {error}")
            raise ValueError(
                f"Configuration validation failed: {', '.join(errors)}")

        if warnings:
            for warning in warnings:
                logger.warning(f"⚠️ Configuration warning: {warning}")

        logger.info(
            f"✅ Configuration validated: {len(enabled_services)} services enabled")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback"""
        return self._config_cache.get(key, default or self.DEFAULTS.get(key))

    def get_admin_ids(self) -> List[int]:
        """Get list of admin user IDs"""
        admin_ids_str = self.get('ADMIN_IDS', '')
        if not admin_ids_str:
            return []

        admin_ids = []
        for aid in admin_ids_str.split(','):
            aid = aid.strip()
            if aid.isdigit():
                admin_ids.append(int(aid))

        return admin_ids

    def get_enabled_services(self) -> List[Dict[str, Any]]:
        """Get list of enabled services with their configuration"""
        services = []

        service_configs = [
            ('RING4', 'RING4_SERVICE_ID', 'RING4_DISPLAY_NAME',
             'RING4_DESCRIPTION', 'RING4_PRIORITY'),
            ('TELEGRAM', 'TELEGRAM_SERVICE_ID', 'TELEGRAM_DISPLAY_NAME',
             'TELEGRAM_DESCRIPTION', 'TELEGRAM_PRIORITY'),
            ('GOOGLE', 'GOOGLE_SERVICE_ID', 'GOOGLE_DISPLAY_NAME',
             'GOOGLE_DESCRIPTION', 'GOOGLE_PRIORITY'),
            ('WHATSAPP', 'WHATSAPP_SERVICE_ID', 'WHATSAPP_DISPLAY_NAME',
             'WHATSAPP_DESCRIPTION', 'WHATSAPP_PRIORITY'),
        ]

        for service_name, id_key, name_key, desc_key, priority_key in service_configs:
            if self.get(f'ENABLE_{service_name}'):
                service = {
                    'id': self.get(id_key),
                    'name': self.get(name_key),
                    'description': self.get(desc_key),
                    'priority': self.get(priority_key),
                    'enabled': True,
                    'service_key': service_name.lower()
                }
                services.append(service)

        # Sort by priority
        services.sort(key=lambda x: x['priority'])
        return services

    def get_service_key_by_id(self, service_id: int) -> Optional[str]:
        """Get service key by service ID"""
        service_mappings = {
            1574: 'ring4',
            22: 'telegram',
            395: 'google',
            1012: 'whatsapp'
        }
        return service_mappings.get(service_id)

    def get_service_profit_margin(self, service_key: str) -> float:
        """Get profit margin for specific service"""
        service_margin_key = f'{service_key.upper()}_PROFIT_MARGIN'
        service_margin = self.get(service_margin_key)

        if service_margin and service_margin.strip():
            try:
                return float(service_margin)
            except ValueError:
                logger.warning(
                    f"Invalid profit margin for {service_key}: {service_margin}")

        return self.get('PROFIT_MARGIN_PERCENT')

    def get_service_fixed_price(self, service_key: str) -> Optional[float]:
        """Get fixed price for specific service (if enabled)"""
        if not self.get('USE_FIXED_PRICING'):
            return None

        price_key = f'{service_key.upper()}_FIXED_PRICE'
        return self.get(price_key)

    def calculate_selling_price(self, api_price: float, service_key: Optional[str] = None) -> float:
        """Calculate selling price with service-specific or global margin"""
        # Use fixed pricing if enabled
        if service_key and self.get('USE_FIXED_PRICING'):
            fixed_price = self.get_service_fixed_price(service_key)
            if fixed_price:
                return round(fixed_price, 2)

        if api_price <= 0:
            return self.get('MIN_PRICE_USD')

        # Get service-specific or global margin
        margin = self.get_service_profit_margin(
            service_key) if service_key else self.get('PROFIT_MARGIN_PERCENT')

        selling_price = api_price * (1 + margin / 100)

        # Apply bounds
        selling_price = max(self.get('MIN_PRICE_USD'), selling_price)
        selling_price = min(self.get('MAX_PRICE_USD'), selling_price)

        return round(selling_price, 2)

    def get_profit_amount(self, api_price: float, service_key: Optional[str] = None) -> float:
        """Calculate profit amount for a given API price"""
        selling_price = self.calculate_selling_price(api_price, service_key)
        return round(selling_price - api_price, 2)

    def get_polling_intervals(self) -> Dict[str, int]:
        """Get adaptive polling intervals"""
        return {
            'initial': self.get('POLLING_INITIAL_INTERVAL'),
            'active': self.get('POLLING_ACTIVE_INTERVAL'),
            'standard': self.get('POLLING_STANDARD_INTERVAL'),
            'extended': self.get('POLLING_EXTENDED_INTERVAL'),
        }

    def is_maintenance_mode(self) -> bool:
        """Check if bot is in maintenance mode"""
        return self.get('MAINTENANCE_MODE')

    def get_maintenance_message(self) -> str:
        """Get maintenance mode message"""
        return self.get('MAINTENANCE_MESSAGE')

    def get_contact_accounts(self) -> List[str]:
        """Get contact account usernames for customer support"""
        accounts = []

        # Get contact accounts from environment
        account1 = self.get('CONTACT_ACCOUNT_1', '') or ''
        account2 = self.get('CONTACT_ACCOUNT_2', '') or ''

        # Strip whitespace and ensure they're strings
        account1 = str(account1).strip() if account1 else ''
        account2 = str(account2).strip() if account2 else ''

        if account1:
            accounts.append(account1)
        if account2:
            accounts.append(account2)

        return accounts

    def validate(self) -> bool:
        """Validate configuration (legacy compatibility)"""
        try:
            self._validate_configuration()
            return True
        except ValueError:
            return False


# Create global configuration instance
Config = ConfigurationManager()


class LegacyConfig:
    """Legacy compatibility wrapper for existing code"""

    def __init__(self, config_manager: ConfigurationManager):
        self._config = config_manager

    @property
    def BOT_TOKEN(self) -> str:
        return self._config.get('BOT_TOKEN')

    @property
    def SMSPOOL_API_KEY(self) -> str:
        return self._config.get('SMSPOOL_API_KEY')

    @property
    def ADMIN_IDS(self) -> List[int]:
        return self._config.get_admin_ids()

    @property
    def BINANCE_WALLET(self) -> str:
        return self._config.get('BINANCE_WALLET')

    @property
    def PROFIT_MARGIN_PERCENT(self) -> float:
        return self._config.get('PROFIT_MARGIN_PERCENT')

    @property
    def MIN_PRICE_USD(self) -> float:
        return self._config.get('MIN_PRICE_USD')

    @property
    def MAX_PRICE_USD(self) -> float:
        return self._config.get('MAX_PRICE_USD')

    @property
    def POLL_INTERVAL(self) -> int:
        return self._config.get('POLL_INTERVAL')

    @property
    def POLL_TIMEOUT(self) -> int:
        return self._config.get('POLL_TIMEOUT')

    @property
    def ORDER_EXPIRES_IN(self) -> int:
        return self._config.get('ORDER_EXPIRES_IN')

    @property
    def DATABASE_PATH(self) -> str:
        return self._config.get('DATABASE_PATH')

    @property
    def SERVICE_PRIORITY(self) -> List[Dict[str, Any]]:
        return self._config.get_enabled_services()

    @property
    def ALTERNATIVE_SERVICES(self) -> List[Dict[str, Any]]:
        return self._config.get_enabled_services()

    @property
    def SMSPOOL_BASE_URL(self) -> str:
        return "https://api.smspool.net"

    @property
    def RING4_SERVICE_ID(self) -> int:
        return self._config.get('RING4_SERVICE_ID')

    @property
    def RING4_COUNTRY_ID(self) -> int:
        return self._config.get('DEFAULT_COUNTRY_ID')

    def calculate_selling_price(self, api_price: float, service_key: Optional[str] = None) -> float:
        """Calculate selling price with profit margin and service-specific pricing"""
        return self._config.calculate_selling_price(api_price, service_key)

    def get_profit_amount(self, api_price: float, service_key: Optional[str] = None) -> float:
        """Calculate profit amount for a given API price with service-specific pricing"""
        return self._config.get_profit_amount(api_price, service_key)

    def get_service_key_by_id(self, service_id: int) -> Optional[str]:
        """Get service key by service ID"""
        return self._config.get_service_key_by_id(service_id)

    def validate(self) -> bool:
        """Validate configuration (legacy method)"""
        return self._config.validate()


# Replace Config with legacy wrapper for backward compatibility
Config = LegacyConfig(Config)
