"""
Configuration module for Ring4 SMS Bot
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    """Configuration class for Ring4 SMS Bot"""

    BOT_TOKEN = os.getenv('BOT_TOKEN', 'DEFAULT_BOT_TOKEN')

    ADMIN_IDS = []
    admin_ids_str = os.getenv('ADMIN_IDS', '')
    if admin_ids_str:
        try:
            ADMIN_IDS = [int(aid.strip()) for aid in admin_ids_str.split(
                ',') if aid.strip().isdigit()]
        except (ValueError, AttributeError):
            ADMIN_IDS = []

    SMSPOOL_API_KEY = os.getenv(
        'SMSPOOL_API_KEY') or os.getenv('PROVIDER_API_KEY')
    SMSPOOL_BASE_URL = "https://api.smspool.net"

    RING4_SERVICE_ID = 1574
    RING4_COUNTRY_ID = 1

    ALTERNATIVE_SERVICES = [
        {'id': 1574, 'name': 'Ring4', 'description': 'Ring4 US numbers'},
        {'id': 22, 'name': 'Telegram', 'description': 'Telegram US numbers'},
        {'id': 1012, 'name': 'WhatsApp', 'description': 'WhatsApp US numbers'},
        {'id': 395, 'name': 'Google', 'description': 'Google/Gmail US numbers'},
    ]

    BINANCE_WALLET = os.getenv('BINANCE_WALLET', '')

    PROFIT_MARGIN_PERCENT = float(
        os.getenv('PROFIT_MARGIN_PERCENT', '5.0'))
    MIN_PRICE_USD = float(os.getenv('MIN_PRICE_USD', '0.15'))
    MAX_PRICE_USD = float(os.getenv('MAX_PRICE_USD', '1.00'))

    SERVICE_PRIORITY = [
        {'id': 1574, 'name': 'Ring4',
            'description': 'Ring4 US numbers (preferred)'},
        {'id': 22, 'name': 'Telegram', 'description': 'Telegram US numbers'},
        {'id': 395, 'name': 'Google', 'description': 'Google/Gmail US numbers'},
        {'id': 1012, 'name': 'WhatsApp', 'description': 'WhatsApp US numbers'},
    ]

    POLL_INTERVAL = 5
    POLL_TIMEOUT = 600
    ORDER_EXPIRES_IN = 600

    DATABASE_PATH = "data/ring4_database.json"

    @classmethod
    def calculate_selling_price(cls, api_price: float) -> float:
        """Calculate selling price with profit margin"""
        if api_price <= 0:
            return cls.MIN_PRICE_USD

        selling_price = api_price * (1 + cls.PROFIT_MARGIN_PERCENT / 100)

        selling_price = max(cls.MIN_PRICE_USD, selling_price)
        selling_price = min(cls.MAX_PRICE_USD, selling_price)

        return round(selling_price, 2)

    @classmethod
    def get_profit_amount(cls, api_price: float) -> float:
        """Calculate profit amount for a given API price"""
        selling_price = cls.calculate_selling_price(api_price)
        return round(selling_price - api_price, 2)

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        required_vars = {
            'BOT_TOKEN': cls.BOT_TOKEN,
            'SMSPOOL_API_KEY': cls.SMSPOOL_API_KEY,
            'BINANCE_WALLET': cls.BINANCE_WALLET
        }

        missing = [k for k, v in required_vars.items(
        ) if not v or v.startswith('DEFAULT_')]

        if missing:
            raise ValueError(
                f"Missing required environment variables: {missing}")

        if not cls.ADMIN_IDS:
            raise ValueError("At least one admin ID must be configured")

        return True
