#!/usr/bin/env python3
"""
Ring4 SMS Bot Configuration Demo
Demonstrates the new centralized configuration system
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.config import ConfigurationManager
except ImportError:
    print("❌ Error: Could not import configuration manager")
    print("Please ensure you're running this from the project root directory")
    sys.exit(1)


def demonstrate_configuration():
    """Demonstrate the new configuration system capabilities"""

    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           🔧 RING4 SMS BOT CONFIGURATION DEMO               ║
║                                                              ║
║              Centralized Control System                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Initialize configuration manager
    print("🔄 Initializing configuration manager...")
    config = ConfigurationManager()

    print("✅ Configuration system loaded successfully!\n")

    # Demonstrate core settings
    print("🔑 CORE AUTHENTICATION:")
    print(
        f"  Bot Token: {'✅ Configured' if config.get('BOT_TOKEN') else '❌ Missing'}")
    print(
        f"  API Key: {'✅ Configured' if config.get('SMSPOOL_API_KEY') else '❌ Missing'}")
    print(f"  Admin IDs: {len(config.get_admin_ids())} configured")
    print(
        f"  Wallet Address: {'✅ Set' if config.get('BINANCE_WALLET') else '❌ Missing'}")

    # Demonstrate services management
    print("\n📱 SERVICES CONFIGURATION:")
    enabled_services = config.get_enabled_services()
    print(f"  Total Services Available: 4")
    print(f"  Services Enabled: {len(enabled_services)}")

    for service in enabled_services:
        priority_text = f"Priority {service['priority']}"
        print(
            f"    ✅ {service['name']}: {service['description']} ({priority_text})")

    # Demonstrate pricing system
    print("\n💰 PRICING CONFIGURATION:")
    if config.get('USE_FIXED_PRICING'):
        print("  Mode: Fixed Pricing")
        for service in enabled_services:
            service_key = service['service_key'].upper()
            fixed_price = config.get_service_fixed_price(service_key)
            if fixed_price:
                print(f"    {service['name']}: ${fixed_price}")
    else:
        print("  Mode: Dynamic Pricing")
        global_margin = config.get('PROFIT_MARGIN_PERCENT')
        print(f"    Global Margin: {global_margin}%")
        print(
            f"    Price Range: ${config.get('MIN_PRICE_USD')} - ${config.get('MAX_PRICE_USD')}")

        # Show service-specific margins
        for service in enabled_services:
            service_key = service['service_key']
            margin = config.get_service_profit_margin(service_key)
            if margin != global_margin:
                print(f"    {service['name']} Margin: {margin}%")

    # Demonstrate wallet system
    print("\n🏦 WALLET SYSTEM:")
    print(
        f"  Status: {'✅ Enabled' if config.get('ENABLE_WALLET_SYSTEM') else '❌ Disabled'}")
    print(f"  Min Deposit: ${config.get('MIN_DEPOSIT_USD')}")
    print(f"  Max Deposit: ${config.get('MAX_DEPOSIT_USD')}")
    auto_approve = config.get('AUTO_APPROVE_BELOW_USD')
    if auto_approve > 0:
        print(f"  Auto-approve below: ${auto_approve}")
    else:
        print(f"  Auto-approve: Disabled")

    # Demonstrate polling configuration
    print("\n🔄 OTP POLLING SYSTEM:")
    intervals = config.get_polling_intervals()
    print(f"  Total Timeout: {config.get('POLL_TIMEOUT')}s")
    print(f"  Adaptive Intervals:")
    print(f"    Initial Phase: {intervals['initial']}s")
    print(f"    Active Phase: {intervals['active']}s")
    print(f"    Standard Phase: {intervals['standard']}s")
    print(f"    Extended Phase: {intervals['extended']}s")

    # Demonstrate business rules
    print("\n📋 BUSINESS RULES:")
    daily_limit = config.get('MAX_ORDERS_PER_USER_PER_DAY')
    hourly_limit = config.get('MAX_ORDERS_PER_USER_PER_HOUR')
    print(
        f"  Max Orders/Day: {daily_limit if daily_limit > 0 else 'Unlimited'}")
    print(
        f"  Max Orders/Hour: {hourly_limit if hourly_limit > 0 else 'Unlimited'}")
    print(
        f"  Auto-refund Timeouts: {'✅ Yes' if config.get('AUTO_REFUND_TIMEOUT') else '❌ No'}")
    print(
        f"  Auto-refund Errors: {'✅ Yes' if config.get('AUTO_REFUND_ERRORS') else '❌ No'}")

    # Demonstrate notifications
    print("\n🔔 NOTIFICATION SETTINGS:")
    notifications = [
        ('NOTIFY_ADMINS_NEW_ORDERS', 'New Orders'),
        ('NOTIFY_ADMINS_FAILED_ORDERS', 'Failed Orders'),
        ('NOTIFY_ADMINS_DEPOSITS', 'Deposit Requests'),
        ('NOTIFY_ADMINS_REFUNDS', 'Refund Requests'),
        ('SEND_DAILY_REPORTS', 'Daily Reports'),
    ]

    for setting, description in notifications:
        status = '✅ Enabled' if config.get(setting) else '❌ Disabled'
        print(f"  {description}: {status}")

    # Demonstrate technical settings
    print("\n⚙️ TECHNICAL CONFIGURATION:")
    print(f"  Environment: {config.get('ENVIRONMENT')}")
    print(f"  Log Level: {config.get('LOG_LEVEL')}")
    print(f"  Database Path: {config.get('DATABASE_PATH')}")
    print(
        f"  Performance Monitoring: {'✅ On' if config.get('ENABLE_PERFORMANCE_MONITORING') else '❌ Off'}")
    print(
        f"  Maintenance Mode: {'🚧 ON' if config.is_maintenance_mode() else '✅ OFF'}")

    # Demonstrate advanced features
    print("\n🚀 ADVANCED FEATURES:")
    print(
        f"  Dynamic Pricing: {'✅ Enabled' if config.get('ENABLE_DYNAMIC_PRICING') else '❌ Disabled'}")
    print(
        f"  Bulk Discounts: {'✅ Enabled' if config.get('ENABLE_BULK_DISCOUNTS') else '❌ Disabled'}")
    print(
        f"  Experimental Features: {'✅ Enabled' if config.get('ENABLE_EXPERIMENTAL_FEATURES') else '❌ Disabled'}")
    print(f"  Service Algorithm: {config.get('SERVICE_SELECTION_ALGORITHM')}")

    # Show configuration file status
    print("\n📁 CONFIGURATION FILES:")
    config_file = Path("config.env")
    env_file = Path(".env")

    if config_file.exists():
        size = config_file.stat().st_size
        print(f"  ✅ config.env ({size} bytes) - Primary configuration")
    else:
        print(f"  ❌ config.env - Not found")

    if env_file.exists():
        size = env_file.stat().st_size
        print(f"  ✅ .env ({size} bytes) - Fallback configuration")
    else:
        print(f"  ❌ .env - Not found")

    # Demonstrate configuration validation
    print("\n✅ CONFIGURATION VALIDATION:")
    try:
        config.validate()
        print("  ✅ All validations passed")
        print("  ✅ Bot is ready to run")
    except Exception as e:
        print(f"  ❌ Validation failed: {str(e)}")
        print("  ⚠️ Please fix configuration issues")

    # Show next steps
    print("\n🎯 NEXT STEPS:")
    print("  1. Run: python3 config_manager.py")
    print("     - Interactive configuration tool")
    print("     - No coding knowledge required")
    print("  ")
    print("  2. Customize your bot:")
    print("     - Add/remove services")
    print("     - Set pricing strategy")
    print("     - Configure business rules")
    print("  ")
    print("  3. Start the bot:")
    print("     - python3 main.py")
    print("     - All settings applied automatically")

    print("\n🔧 CONFIGURATION BENEFITS:")
    print("  ✅ No code editing required")
    print("  ✅ Centralized control")
    print("  ✅ Interactive setup wizard")
    print("  ✅ Automatic validation")
    print("  ✅ Backup and restore")
    print("  ✅ Hot-reload support")
    print("  ✅ Advanced features accessible")

    print("\n" + "="*70)
    print("🎉 Configuration system demo completed!")
    print("See CONFIGURATION.md for detailed documentation.")
    print("="*70)


if __name__ == "__main__":
    demonstrate_configuration()
