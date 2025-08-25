#!/usr/bin/env python3
"""
Ring4 SMS Bot Configuration Manager
Interactive configuration tool for non-technical users
"""
import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.config import ConfigurationManager
except ImportError:
    print("❌ Error: Could not import configuration manager")
    print("Please ensure you're running this from the project root directory")
    sys.exit(1)


class ConfigurationTool:
    """Interactive configuration management tool"""

    def __init__(self):
        self.config_file = Path("config.env")
        self.backup_dir = Path("config_backups")
        self.backup_dir.mkdir(exist_ok=True)

    def run(self):
        """Main configuration tool interface"""
        self.show_banner()

        while True:
            choice = self.show_main_menu()

            if choice == '1':
                self.setup_wizard()
            elif choice == '2':
                self.edit_services()
            elif choice == '3':
                self.edit_pricing()
            elif choice == '4':
                self.edit_business_rules()
            elif choice == '5':
                self.edit_technical_settings()
            elif choice == '6':
                self.validate_configuration()
            elif choice == '7':
                self.backup_restore_menu()
            elif choice == '8':
                self.view_current_config()
            elif choice == '9':
                self.export_config_summary()
            elif choice == '0':
                print("\n👋 Configuration tool closed. Restart the bot to apply changes.")
                break
            else:
                print("❌ Invalid choice. Please try again.")

    def show_banner(self):
        """Display tool banner"""
        print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🔧 RING4 SMS BOT CONFIGURATION TOOL            ║
║                                                              ║
║                  Easy Setup for Non-Coders                  ║
║                                                              ║
║  📋 Features:                                                ║
║    • Interactive setup wizard                               ║
║    • Service management (add/remove/configure)              ║
║    • Pricing control (margins, fixed prices)               ║
║    • Business rules configuration                           ║
║    • Technical settings management                          ║
║    • Configuration validation                               ║
║    • Backup and restore                                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """)

    def show_main_menu(self) -> str:
        """Display main menu and get user choice"""
        print("\n🔧 CONFIGURATION MANAGER")
        print("=" * 50)
        print("1. 🚀 Quick Setup Wizard (Recommended for new users)")
        print("2. 📱 Manage Services (Add/Remove/Configure services)")
        print("3. 💰 Configure Pricing (Margins, fixed prices, limits)")
        print("4. 📋 Business Rules (Orders, refunds, notifications)")
        print("5. ⚙️  Technical Settings (Polling, database, logs)")
        print("6. ✅ Validate Configuration")
        print("7. 💾 Backup & Restore")
        print("8. 👀 View Current Configuration")
        print("9. 📄 Export Configuration Summary")
        print("0. 🚪 Exit")
        print()
        return input("Choose an option (0-9): ").strip()

    def setup_wizard(self):
        """Interactive setup wizard for new users"""
        print("\n🚀 QUICK SETUP WIZARD")
        print("=" * 50)
        print("This wizard will help you configure the essential settings.")
        print("You can always modify these later using the other menu options.\n")

        # Backup existing config
        if self.config_file.exists():
            self.create_backup("before_wizard")
            print("✅ Existing configuration backed up")

        config = {}

        # Core settings
        print("📝 STEP 1: Core Authentication")
        config['BOT_TOKEN'] = self.get_input(
            "Telegram Bot Token (from @BotFather)",
            required=True,
            validation=lambda x: len(x) > 20
        )

        config['SMSPOOL_API_KEY'] = self.get_input(
            "SMS Service API Key",
            required=True,
            validation=lambda x: len(x) > 10
        )

        admin_ids = self.get_input(
            "Admin User IDs (comma-separated, get from @userinfobot)",
            required=True,
            validation=lambda x: all(id.strip().isdigit()
                                     for id in x.split(','))
        )
        config['ADMIN_IDS'] = admin_ids

        config['BINANCE_WALLET'] = self.get_input(
            "Crypto Wallet Address for deposits",
            required=True
        )

        # Services
        print("\n📱 STEP 2: Services Configuration")
        print("Which SMS services would you like to enable?")

        services = [
            ('RING4', 'Ring4 (Recommended - best reliability)'),
            ('TELEGRAM', 'Telegram'),
            ('GOOGLE', 'Google/Gmail'),
            ('WHATSAPP', 'WhatsApp')
        ]

        for service_key, service_desc in services:
            enable = self.get_yes_no(f"Enable {service_desc}?", default=True)
            config[f'ENABLE_{service_key}'] = str(enable).lower()

        # Pricing
        print("\n💰 STEP 3: Pricing Configuration")

        pricing_mode = self.get_choice(
            "Choose pricing mode",
            [
                ("dynamic", "Dynamic pricing (cost + margin %)"),
                ("fixed", "Fixed pricing (set exact prices)")
            ],
            default="dynamic"
        )

        if pricing_mode == "dynamic":
            config['USE_FIXED_PRICING'] = 'false'
            config['PROFIT_MARGIN_PERCENT'] = self.get_input(
                "Profit margin percentage (recommended: 5-15%)",
                default="5.0",
                validation=lambda x: 0 <= float(x) <= 100
            )
        else:
            config['USE_FIXED_PRICING'] = 'true'
            if config.get('ENABLE_RING4') == 'true':
                config['RING4_FIXED_PRICE'] = self.get_input(
                    "Ring4 fixed price (USD)",
                    default="0.17",
                    validation=lambda x: float(x) > 0
                )
            if config.get('ENABLE_TELEGRAM') == 'true':
                config['TELEGRAM_FIXED_PRICE'] = self.get_input(
                    "Telegram fixed price (USD)",
                    default="0.25",
                    validation=lambda x: float(x) > 0
                )

        # Wallet settings
        print("\n🏦 STEP 4: Wallet Configuration")
        config['MIN_DEPOSIT_USD'] = self.get_input(
            "Minimum deposit amount (USD)",
            default="5.00",
            validation=lambda x: float(x) >= 1.0
        )

        config['MAX_DEPOSIT_USD'] = self.get_input(
            "Maximum deposit amount (USD)",
            default="1000.00",
            validation=lambda x: float(x) >= float(config['MIN_DEPOSIT_USD'])
        )

        # Write configuration
        self.write_config(config)

        print("\n✅ SETUP COMPLETED!")
        print("Your bot is now configured and ready to use.")
        print("You can fine-tune settings using the other menu options.")
        print("\n🚀 Start your bot with: python3 main.py")

    def edit_services(self):
        """Service management interface"""
        print("\n📱 SERVICES MANAGEMENT")
        print("=" * 50)

        while True:
            # Reload config each iteration to show current state
            current_config = self.load_current_config()

            print("\nCurrently enabled services:")
            services = [
                ('RING4', 'Ring4'),
                ('TELEGRAM', 'Telegram'),
                ('GOOGLE', 'Google/Gmail'),
                ('WHATSAPP', 'WhatsApp')
            ]

            for service_key, service_name in services:
                enabled = current_config.get(
                    f'ENABLE_{service_key}', 'true') == 'true'
                status = "✅ Enabled" if enabled else "❌ Disabled"
                priority = current_config.get(f'{service_key}_PRIORITY', 'N/A')
                display_name = current_config.get(
                    f'{service_key}_DISPLAY_NAME', service_name)
                print(f"  {display_name}: {status} (Priority: {priority})")

            print("\nOptions:")
            print("1. Enable/Disable services")
            print("2. Change service priorities")
            print("3. Customize service names")
            print("4. Configure service-specific settings")
            print("0. Back to main menu")

            choice = input("\nChoose option: ").strip()

            if choice == '1':
                self.toggle_services(current_config)
            elif choice == '2':
                self.set_service_priorities(current_config)
            elif choice == '3':
                self.customize_service_names(current_config)
            elif choice == '4':
                self.configure_service_settings(current_config)
            elif choice == '0':
                break
            else:
                print("❌ Invalid choice")

    def edit_pricing(self):
        """Pricing configuration interface"""
        print("\n💰 PRICING CONFIGURATION")
        print("=" * 50)

        while True:
            # Reload config each iteration to show current state
            current_config = self.load_current_config()

            # Show current pricing
            use_fixed = current_config.get(
                'USE_FIXED_PRICING', 'false') == 'true'
            print(
                f"\nCurrent pricing mode: {'Fixed Pricing' if use_fixed else 'Dynamic Pricing'}")

            if use_fixed:
                print("Fixed prices:")
                for service in ['RING4', 'TELEGRAM', 'GOOGLE', 'WHATSAPP']:
                    price = current_config.get(
                        f'{service}_FIXED_PRICE', 'Not set')
                    print(f"  {service}: ${price}")
            else:
                margin = current_config.get('PROFIT_MARGIN_PERCENT', '5.0')
                min_price = current_config.get('MIN_PRICE_USD', '0.15')
                max_price = current_config.get('MAX_PRICE_USD', '1.00')
                print(f"Profit margin: {margin}%")
                print(f"Price range: ${min_price} - ${max_price}")

            print("\nOptions:")
            print("1. Switch pricing mode (Fixed ↔ Dynamic)")
            print("2. Configure profit margins")
            print("3. Set fixed prices")
            print("4. Set price limits")
            print("5. Service-specific pricing")
            print("0. Back to main menu")

            choice = input("\nChoose option: ").strip()

            if choice == '1':
                self.switch_pricing_mode(current_config)
            elif choice == '2':
                self.configure_margins(current_config)
            elif choice == '3':
                self.set_fixed_prices(current_config)
            elif choice == '4':
                self.set_price_limits(current_config)
            elif choice == '5':
                self.configure_service_pricing(current_config)
            elif choice == '0':
                break
            else:
                print("❌ Invalid choice")

    def edit_business_rules(self):
        """Business rules configuration"""
        print("\n📋 BUSINESS RULES CONFIGURATION")
        print("=" * 50)

        current_config = self.load_current_config()

        sections = [
            ("Order Limits", self.configure_order_limits),
            ("Refund Policies", self.configure_refund_policies),
            ("Notifications", self.configure_notifications),
            ("Security Settings", self.configure_security),
        ]

        while True:
            print("\nBusiness rules sections:")
            for i, (name, _) in enumerate(sections, 1):
                print(f"{i}. {name}")
            print("0. Back to main menu")

            choice = input("\nChoose section: ").strip()

            if choice == '0':
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(sections):
                sections[int(choice) - 1][1](current_config)
            else:
                print("❌ Invalid choice")

    def edit_technical_settings(self):
        """Technical settings configuration"""
        print("\n⚙️ TECHNICAL SETTINGS")
        print("=" * 50)

        current_config = self.load_current_config()

        while True:
            print("\nTechnical settings:")
            print("1. OTP Polling Configuration")
            print("2. Database Settings")
            print("3. Logging Configuration")
            print("4. Performance Settings")
            print("5. Maintenance Mode")
            print("0. Back to main menu")

            choice = input("\nChoose section: ").strip()

            if choice == '1':
                self.configure_polling(current_config)
            elif choice == '2':
                self.configure_database(current_config)
            elif choice == '3':
                self.configure_logging(current_config)
            elif choice == '4':
                self.configure_performance(current_config)
            elif choice == '5':
                self.configure_maintenance(current_config)
            elif choice == '0':
                break
            else:
                print("❌ Invalid choice")

    def validate_configuration(self):
        """Validate current configuration"""
        print("\n✅ CONFIGURATION VALIDATION")
        print("=" * 50)

        try:
            config_manager = ConfigurationManager()
            config_manager.reload_config()

            print("✅ Configuration loaded successfully")

            # Check required fields
            required_fields = ['BOT_TOKEN', 'SMSPOOL_API_KEY', 'ADMIN_IDS']
            missing = []

            for field in required_fields:
                if not config_manager.get(field):
                    missing.append(field)

            if missing:
                print(f"❌ Missing required fields: {', '.join(missing)}")
            else:
                print("✅ All required fields present")

            # Check services
            enabled_services = config_manager.get_enabled_services()
            if enabled_services:
                print(f"✅ {len(enabled_services)} services enabled")
                for service in enabled_services:
                    print(
                        f"   • {service['name']} (Priority: {service['priority']})")
            else:
                print("⚠️ No services are enabled")

            # Check admin IDs
            admin_ids = config_manager.get_admin_ids()
            if admin_ids:
                print(f"✅ {len(admin_ids)} admin(s) configured")
            else:
                print("❌ No admin IDs configured")

            # Check pricing
            if config_manager.get('USE_FIXED_PRICING'):
                print("✅ Using fixed pricing mode")
            else:
                margin = config_manager.get('PROFIT_MARGIN_PERCENT')
                print(f"✅ Using dynamic pricing (margin: {margin}%)")

            print("\n✅ Configuration validation completed")

        except (ImportError, AttributeError) as e:
            print(f"❌ Configuration validation failed: {str(e)}")

    def backup_restore_menu(self):
        """Backup and restore interface"""
        print("\n💾 BACKUP & RESTORE")
        print("=" * 50)

        while True:
            # List existing backups
            backups = list(self.backup_dir.glob("*.env"))

            print(f"\nAvailable backups ({len(backups)}):")
            if backups:
                for i, backup in enumerate(sorted(backups), 1):
                    size = backup.stat().st_size
                    mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                    print(
                        f"  {i}. {backup.name} ({size} bytes, {mtime.strftime('%Y-%m-%d %H:%M')})")
            else:
                print("  No backups found")

            print("\nOptions:")
            print("1. Create backup")
            print("2. Restore from backup")
            print("3. Delete backup")
            print("0. Back to main menu")

            choice = input("\nChoose option: ").strip()

            if choice == '1':
                name = input("Backup name (optional): ").strip()
                self.create_backup(name or "manual")
            elif choice == '2' and backups:
                self.restore_backup(backups)
            elif choice == '3' and backups:
                self.delete_backup(backups)
            elif choice == '0':
                break
            else:
                print("❌ Invalid choice or no backups available")

    def view_current_config(self):
        """Display current configuration"""
        print("\n👀 CURRENT CONFIGURATION")
        print("=" * 50)

        if not self.config_file.exists():
            print("❌ No configuration file found")
            return

        try:
            config_manager = ConfigurationManager()
            config_manager.reload_config()

            # Core settings
            print("\n🔑 CORE SETTINGS:")
            print(
                f"  Bot Token: {'✅ Set' if config_manager.get('BOT_TOKEN') else '❌ Missing'}")
            print(
                f"  API Key: {'✅ Set' if config_manager.get('SMSPOOL_API_KEY') else '❌ Missing'}")
            print(
                f"  Admin IDs: {len(config_manager.get_admin_ids())} configured")
            print(
                f"  Wallet: {'✅ Set' if config_manager.get('BINANCE_WALLET') else '❌ Missing'}")

            # Services
            print("\n📱 SERVICES:")
            services = config_manager.get_enabled_services()
            for service in services:
                print(
                    f"  ✅ {service['name']} (Priority: {service['priority']})")

            # Pricing
            print("\n💰 PRICING:")
            if config_manager.get('USE_FIXED_PRICING'):
                print("  Mode: Fixed Pricing")
                for service in ['RING4', 'TELEGRAM', 'GOOGLE', 'WHATSAPP']:
                    price = config_manager.get(f'{service}_FIXED_PRICE')
                    if price:
                        print(f"    {service}: ${price}")
            else:
                print("  Mode: Dynamic Pricing")
                print(
                    f"  Margin: {config_manager.get('PROFIT_MARGIN_PERCENT')}%")
                print(
                    f"  Range: ${config_manager.get('MIN_PRICE_USD')} - ${config_manager.get('MAX_PRICE_USD')}")

            # Wallet
            print("\n🏦 WALLET:")
            print(f"  Min Deposit: ${config_manager.get('MIN_DEPOSIT_USD')}")
            print(f"  Max Deposit: ${config_manager.get('MAX_DEPOSIT_USD')}")

            # Technical
            print("\n⚙️ TECHNICAL:")
            print(f"  Environment: {config_manager.get('ENVIRONMENT')}")
            print(f"  Log Level: {config_manager.get('LOG_LEVEL')}")
            print(
                f"  Maintenance: {'ON' if config_manager.get('MAINTENANCE_MODE') else 'OFF'}")

        except (ImportError, AttributeError, KeyError) as e:
            print(f"❌ Error reading configuration: {str(e)}")

    def export_config_summary(self):
        """Export configuration summary to file"""
        print("\n📄 EXPORT CONFIGURATION SUMMARY")
        print("=" * 50)

        try:
            config_manager = ConfigurationManager()
            config_manager.reload_config()

            summary = {
                "export_date": datetime.now().isoformat(),
                "bot_status": {
                    "configured": bool(config_manager.get('BOT_TOKEN')),
                    "services_enabled": len(config_manager.get_enabled_services()),
                    "admins_configured": len(config_manager.get_admin_ids()),
                },
                "services": [
                    {
                        "name": service['name'],
                        "enabled": True,
                        "priority": service['priority'],
                        "description": service['description']
                    }
                    for service in config_manager.get_enabled_services()
                ],
                "pricing": {
                    "mode": "fixed" if config_manager.get('USE_FIXED_PRICING') else "dynamic",
                    "margin_percent": config_manager.get('PROFIT_MARGIN_PERCENT'),
                    "min_price": config_manager.get('MIN_PRICE_USD'),
                    "max_price": config_manager.get('MAX_PRICE_USD'),
                },
                "wallet": {
                    "min_deposit": config_manager.get('MIN_DEPOSIT_USD'),
                    "max_deposit": config_manager.get('MAX_DEPOSIT_USD'),
                },
                "technical": {
                    "environment": config_manager.get('ENVIRONMENT'),
                    "log_level": config_manager.get('LOG_LEVEL'),
                    "maintenance_mode": config_manager.get('MAINTENANCE_MODE'),
                }
            }

            export_file = f"config_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)

            print(f"✅ Configuration summary exported to: {export_file}")

        except (IOError, OSError) as e:
            print(f"❌ Export failed: {str(e)}")

    # Helper methods
    def get_input(self, prompt: str, default: str = "", required: bool = False, validation=None) -> str:
        """Get user input with validation"""
        while True:
            if default:
                value = input(f"{prompt} [{default}]: ").strip() or default
            else:
                value = input(f"{prompt}: ").strip()

            if required and not value:
                print("❌ This field is required")
                continue

            if validation:
                try:
                    if not validation(value):
                        print("❌ Invalid value")
                        continue
                except (ValueError, TypeError):
                    print("❌ Invalid value format")
                    continue

            return value

    def get_yes_no(self, prompt: str, default: bool = False) -> bool:
        """Get yes/no input"""
        default_str = "Y/n" if default else "y/N"
        while True:
            value = input(f"{prompt} [{default_str}]: ").strip().lower()
            if not value:
                return default
            if value in ['y', 'yes', 'true', '1']:
                return True
            elif value in ['n', 'no', 'false', '0']:
                return False
            else:
                print("❌ Please enter y/yes or n/no")

    def get_choice(self, prompt: str, choices: List[tuple], default: Optional[str] = None) -> str:
        """Get choice from options"""
        while True:
            print(f"\n{prompt}:")
            for i, (value, description) in enumerate(choices, 1):
                marker = " (default)" if value == default else ""
                print(f"  {i}. {description}{marker}")

            if default:
                choice_input = input(
                    f"\nChoose (1-{len(choices)}) [default: {default}]: ").strip()
                if not choice_input:
                    return default
            else:
                choice_input = input(f"\nChoose (1-{len(choices)}): ").strip()

            if choice_input.isdigit():
                choice_num = int(choice_input)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1][0]

            print("❌ Invalid choice")

    def load_current_config(self) -> Dict[str, str]:
        """Load current configuration from file"""
        config = {}
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        return config

    def write_config(self, config: Dict[str, str]):
        """Write configuration to file"""
        # Read the template to preserve comments and structure
        template_lines = []
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                template_lines = f.readlines()

        # Create a copy to avoid modifying the original
        config_copy = config.copy()

        # Write updated config
        with open(self.config_file, 'w', encoding='utf-8') as f:
            if template_lines:
                # Update existing file
                for line in template_lines:
                    if '=' in line and not line.strip().startswith('#'):
                        key = line.split('=')[0].strip()
                        if key in config_copy:
                            f.write(f"{key}={config_copy[key]}\n")
                            del config_copy[key]
                        else:
                            f.write(line)
                    else:
                        f.write(line)

                # Add any new config values
                if config_copy:
                    f.write("\n# Additional settings\n")
                    for key, value in config_copy.items():
                        f.write(f"{key}={value}\n")
            else:
                # Create new file
                f.write("# Ring4 SMS Bot Configuration\n")
                for key, value in config.items():
                    f.write(f"{key}={value}\n")

        print(f"✅ Configuration saved to {self.config_file}")

    def create_backup(self, name: str = ""):
        """Create configuration backup"""
        if not self.config_file.exists():
            print("❌ No configuration file to backup")
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"config_backup_{name}_{timestamp}.env" if name else f"config_backup_{timestamp}.env"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(self.config_file, backup_path)
        print(f"✅ Backup created: {backup_path}")

    def restore_backup(self, backups: List[Path]):
        """Restore from backup"""
        print("\nSelect backup to restore:")
        for i, backup in enumerate(sorted(backups), 1):
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"  {i}. {backup.name} ({mtime.strftime('%Y-%m-%d %H:%M')})")

        try:
            choice = int(input("Choose backup number: ")) - 1
            if 0 <= choice < len(backups):
                backup_file = sorted(backups)[choice]

                # Create backup of current config
                if self.config_file.exists():
                    self.create_backup("before_restore")

                shutil.copy2(backup_file, self.config_file)
                print(f"✅ Configuration restored from {backup_file.name}")
            else:
                print("❌ Invalid backup number")
        except ValueError:
            print("❌ Invalid input")

    def delete_backup(self, backups: List[Path]):
        """Delete backup file"""
        print("\nSelect backup to delete:")
        for i, backup in enumerate(sorted(backups), 1):
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"  {i}. {backup.name} ({mtime.strftime('%Y-%m-%d %H:%M')})")

        try:
            choice = int(input("Choose backup number to delete: ")) - 1
            if 0 <= choice < len(backups):
                backup_file = sorted(backups)[choice]

                if self.get_yes_no(f"Delete {backup_file.name}?"):
                    backup_file.unlink()
                    print(f"✅ Backup {backup_file.name} deleted")
            else:
                print("❌ Invalid backup number")
        except ValueError:
            print("❌ Invalid input")

    # Configuration section methods (simplified for space)
    def toggle_services(self, config: Dict[str, str]):
        """Toggle service enable/disable"""
        services = [('RING4', 'Ring4'), ('TELEGRAM', 'Telegram'),
                    ('GOOGLE', 'Google'), ('WHATSAPP', 'WhatsApp')]

        for service_key, service_name in services:
            current = config.get(f'ENABLE_{service_key}', 'true') == 'true'
            new_value = self.get_yes_no(
                f"Enable {service_name}?", default=current)
            config[f'ENABLE_{service_key}'] = str(new_value).lower()

        self.write_config(config)

    def set_service_priorities(self, config: Dict[str, str]):
        """Set service priorities"""
        services = ['RING4', 'TELEGRAM', 'GOOGLE', 'WHATSAPP']

        print("\nSet service priorities (1=highest, 4=lowest):")
        for service in services:
            current = config.get(f'{service}_PRIORITY', '1')
            priority = self.get_input(f"{service} priority", default=current,
                                      validation=lambda x: x.isdigit() and 1 <= int(x) <= 4)
            config[f'{service}_PRIORITY'] = priority

        self.write_config(config)

    def switch_pricing_mode(self, config: Dict[str, str]):
        """Switch between fixed and dynamic pricing"""
        current_mode = config.get('USE_FIXED_PRICING', 'false') == 'true'
        new_mode = not current_mode

        mode_name = "Fixed" if new_mode else "Dynamic"
        if self.get_yes_no(f"Switch to {mode_name} pricing mode?"):
            config['USE_FIXED_PRICING'] = str(new_mode).lower()
            self.write_config(config)
            print(f"✅ Switched to {mode_name} pricing mode")

    def configure_margins(self, config: Dict[str, str]):
        """Configure profit margins"""
        current = config.get('PROFIT_MARGIN_PERCENT', '5.0')
        margin = self.get_input("Global profit margin (%)", default=current,
                                validation=lambda x: 0 <= float(x) <= 100)
        config['PROFIT_MARGIN_PERCENT'] = margin
        self.write_config(config)

    def set_fixed_prices(self, config: Dict[str, str]):
        """Set fixed prices for services"""
        config['USE_FIXED_PRICING'] = 'true'

        services = [('RING4', '0.17'), ('TELEGRAM', '0.25'),
                    ('GOOGLE', '0.42'), ('WHATSAPP', '0.35')]

        for service_key, default_price in services:
            if config.get(f'ENABLE_{service_key}', 'true') == 'true':
                current = config.get(
                    f'{service_key}_FIXED_PRICE', default_price)
                price = self.get_input(f"{service_key} fixed price ($)", default=current,
                                       validation=lambda x: float(x) > 0)
                config[f'{service_key}_FIXED_PRICE'] = price

        self.write_config(config)

    def configure_order_limits(self, config: Dict[str, str]):
        """Configure order limits"""
        daily_limit = config.get('MAX_ORDERS_PER_USER_PER_DAY', '10')
        hourly_limit = config.get('MAX_ORDERS_PER_USER_PER_HOUR', '3')

        config['MAX_ORDERS_PER_USER_PER_DAY'] = self.get_input(
            "Max orders per user per day (0=unlimited)", default=daily_limit,
            validation=lambda x: x.isdigit() and int(x) >= 0
        )

        config['MAX_ORDERS_PER_USER_PER_HOUR'] = self.get_input(
            "Max orders per user per hour (0=unlimited)", default=hourly_limit,
            validation=lambda x: x.isdigit() and int(x) >= 0
        )

        self.write_config(config)

    def configure_polling(self, config: Dict[str, str]):
        """Configure OTP polling settings"""
        print("\nOTP Polling Configuration:")

        settings = [
            ('POLL_TIMEOUT', 'Total polling timeout (seconds)', '600'),
            ('POLLING_INITIAL_INTERVAL', 'Initial polling interval (seconds)', '2'),
            ('POLLING_ACTIVE_INTERVAL', 'Active polling interval (seconds)', '3'),
            ('POLLING_STANDARD_INTERVAL', 'Standard polling interval (seconds)', '5'),
            ('POLLING_EXTENDED_INTERVAL', 'Extended polling interval (seconds)', '10'),
        ]

        for key, description, default in settings:
            current = config.get(key, default)
            value = self.get_input(description, default=current,
                                   validation=lambda x: x.isdigit() and int(x) > 0)
            config[key] = value

        self.write_config(config)

    def configure_maintenance(self, config: Dict[str, str]):
        """Configure maintenance mode"""
        current_mode = config.get('MAINTENANCE_MODE', 'false') == 'true'

        enable_maintenance = self.get_yes_no(
            "Enable maintenance mode?", default=current_mode)
        config['MAINTENANCE_MODE'] = str(enable_maintenance).lower()

        if enable_maintenance:
            current_msg = config.get(
                'MAINTENANCE_MESSAGE', 'Bot is currently under maintenance. Please try again later.')
            message = self.get_input(
                "Maintenance message", default=current_msg)
            config['MAINTENANCE_MESSAGE'] = message

        self.write_config(config)

    def customize_service_names(self, config: Dict[str, str]):
        """Customize service display names"""
        services = [('RING4', 'Ring4'), ('TELEGRAM', 'Telegram'),
                    ('GOOGLE', 'Google'), ('WHATSAPP', 'WhatsApp')]

        for service_key, default_name in services:
            if config.get(f'ENABLE_{service_key}', 'true') == 'true':
                current = config.get(
                    f'{service_key}_DISPLAY_NAME', default_name)
                name = self.get_input(
                    f"{service_key} display name", default=current)
                config[f'{service_key}_DISPLAY_NAME'] = name

        self.write_config(config)

    def configure_service_settings(self, config: Dict[str, str]):
        """Configure service-specific settings"""
        print("Service-specific settings configuration")
        # This could be expanded for advanced service settings
        self.customize_service_names(config)

    def set_price_limits(self, config: Dict[str, str]):
        """Set global price limits"""
        min_price = config.get('MIN_PRICE_USD', '0.15')
        max_price = config.get('MAX_PRICE_USD', '1.00')

        config['MIN_PRICE_USD'] = self.get_input(
            "Minimum price ($)", default=min_price,
            validation=lambda x: float(x) > 0
        )

        config['MAX_PRICE_USD'] = self.get_input(
            "Maximum price ($)", default=max_price,
            validation=lambda x: float(x) > float(config['MIN_PRICE_USD'])
        )

        self.write_config(config)

    def configure_service_pricing(self, config: Dict[str, str]):
        """Configure service-specific pricing"""
        print("Configure individual service profit margins:")

        services = ['RING4', 'TELEGRAM', 'GOOGLE', 'WHATSAPP']

        for service in services:
            if config.get(f'ENABLE_{service}', 'true') == 'true':
                current = config.get(f'{service}_PROFIT_MARGIN', '')
                margin = self.get_input(
                    f"{service} profit margin (% or leave empty for global)",
                    default=current
                )
                config[f'{service}_PROFIT_MARGIN'] = margin

        self.write_config(config)

    def configure_refund_policies(self, config: Dict[str, str]):
        """Configure refund policies"""
        auto_timeout = config.get('AUTO_REFUND_TIMEOUT', 'true') == 'true'
        auto_errors = config.get('AUTO_REFUND_ERRORS', 'true') == 'true'

        config['AUTO_REFUND_TIMEOUT'] = str(self.get_yes_no(
            "Auto-refund timeout orders?", default=auto_timeout
        )).lower()

        config['AUTO_REFUND_ERRORS'] = str(self.get_yes_no(
            "Auto-refund error orders?", default=auto_errors
        )).lower()

        self.write_config(config)

    def configure_notifications(self, config: Dict[str, str]):
        """Configure notification settings"""
        settings = [
            ('NOTIFY_ADMINS_NEW_ORDERS', 'Notify admins of new orders?', 'false'),
            ('NOTIFY_ADMINS_FAILED_ORDERS',
             'Notify admins of failed orders?', 'true'),
            ('NOTIFY_ADMINS_DEPOSITS', 'Notify admins of deposit requests?', 'true'),
            ('NOTIFY_ADMINS_REFUNDS', 'Notify admins of refund requests?', 'true'),
            ('SEND_DAILY_REPORTS', 'Send daily revenue reports?', 'true'),
        ]

        for key, question, default in settings:
            current = config.get(key, default) == 'true'
            value = self.get_yes_no(question, default=current)
            config[key] = str(value).lower()

        if config.get('SEND_DAILY_REPORTS') == 'true':
            report_time = config.get('DAILY_REPORT_TIME', '09:00')
            config['DAILY_REPORT_TIME'] = self.get_input(
                "Daily report time (HH:MM)", default=report_time
            )

        self.write_config(config)

    def configure_security(self, config: Dict[str, str]):
        """Configure security settings"""
        settings = [
            ('RATE_LIMIT_PER_MINUTE', 'Rate limit per user (requests/minute)', '10'),
            ('LARGE_DEPOSIT_THRESHOLD', 'Large deposit threshold ($)', '100.00'),
        ]

        for key, description, default in settings:
            current = config.get(key, default)
            value = self.get_input(description, default=current,
                                   validation=lambda x: float(x) > 0)
            config[key] = value

        # Boolean settings
        bool_settings = [
            ('AUTO_BLOCK_SUSPICIOUS', 'Auto-block suspicious users?', 'false'),
            ('REQUIRE_VERIFICATION_FOR_LARGE_DEPOSITS',
             'Require verification for large deposits?', 'true'),
            ('ENABLE_IP_LOGGING', 'Enable IP logging?', 'false'),
        ]

        for key, question, default in bool_settings:
            current = config.get(key, default) == 'true'
            value = self.get_yes_no(question, default=current)
            config[key] = str(value).lower()

        self.write_config(config)

    def configure_database(self, config: Dict[str, str]):
        """Configure database settings"""
        db_path = config.get('DATABASE_PATH', 'data/ring4_database.json')
        backup_interval = config.get('DATABASE_BACKUP_INTERVAL', '24')

        config['DATABASE_PATH'] = self.get_input(
            "Database file path", default=db_path
        )

        config['DATABASE_BACKUP_INTERVAL'] = self.get_input(
            "Database backup interval (hours)", default=backup_interval,
            validation=lambda x: x.isdigit() and int(x) > 0
        )

        auto_optimize = config.get('AUTO_OPTIMIZE_DATABASE', 'true') == 'true'
        config['AUTO_OPTIMIZE_DATABASE'] = str(self.get_yes_no(
            "Enable automatic database optimization?", default=auto_optimize
        )).lower()

        self.write_config(config)

    def configure_logging(self, config: Dict[str, str]):
        """Configure logging settings"""
        log_level = config.get('LOG_LEVEL', 'INFO')
        max_log_size = config.get('MAX_LOG_FILE_SIZE', '100')
        log_files_keep = config.get('LOG_FILES_TO_KEEP', '7')

        log_levels = [
            ('DEBUG', 'Debug (most verbose)'),
            ('INFO', 'Info (recommended)'),
            ('WARNING', 'Warning (less verbose)'),
            ('ERROR', 'Error (least verbose)')
        ]

        config['LOG_LEVEL'] = self.get_choice(
            "Log level", log_levels, default=log_level
        )

        config['MAX_LOG_FILE_SIZE'] = self.get_input(
            "Maximum log file size (MB)", default=max_log_size,
            validation=lambda x: x.isdigit() and int(x) > 0
        )

        config['LOG_FILES_TO_KEEP'] = self.get_input(
            "Number of log files to keep", default=log_files_keep,
            validation=lambda x: x.isdigit() and int(x) > 0
        )

        self.write_config(config)

    def configure_performance(self, config: Dict[str, str]):
        """Configure performance settings"""
        api_timeout = config.get('API_TIMEOUT_SECONDS', '10')
        perf_monitoring = config.get(
            'ENABLE_PERFORMANCE_MONITORING', 'true') == 'true'
        perf_threshold = config.get('PERFORMANCE_ALERT_THRESHOLD', '5.0')

        config['API_TIMEOUT_SECONDS'] = self.get_input(
            "API timeout (seconds)", default=api_timeout,
            validation=lambda x: x.isdigit() and int(x) > 0
        )

        config['ENABLE_PERFORMANCE_MONITORING'] = str(self.get_yes_no(
            "Enable performance monitoring?", default=perf_monitoring
        )).lower()

        if config['ENABLE_PERFORMANCE_MONITORING'] == 'true':
            config['PERFORMANCE_ALERT_THRESHOLD'] = self.get_input(
                "Performance alert threshold (seconds)", default=perf_threshold,
                validation=lambda x: float(x) > 0
            )

        self.write_config(config)


if __name__ == "__main__":
    tool = ConfigurationTool()
    tool.run()
