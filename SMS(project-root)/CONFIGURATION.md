# 🔧 Ring4 SMS Bot - Configuration Management System

## Overview

This bot now features a **comprehensive centralized configuration system** that allows non-technical users to control all bot settings from one place. No coding knowledge required!

## 🚀 Quick Start

### For New Users (Setup Wizard)

```bash
# Run the interactive configuration tool
python3 config_manager.py

# Choose option 1: Quick Setup Wizard
# Follow the prompts to configure:
# - Bot token
# - API keys
# - Admin users
# - Services
# - Pricing
# - Wallet settings
```

### For Existing Users

```bash
# Run the configuration manager
python3 config_manager.py

# Use various menu options to customize:
# - Services (enable/disable, priorities)
# - Pricing (margins, fixed prices)
# - Business rules
# - Technical settings
```

## 📁 Configuration Files

### Primary Configuration

- **`config.env`** - Main configuration file with all settings
- **`config_manager.py`** - Interactive configuration tool
- **`.env`** - Fallback configuration (legacy support)

### Backup System

- **`config_backups/`** - Automatic backups of configuration changes
- Timestamped backups created before major changes
- Easy restore functionality

## 🛠️ Configuration Sections

### 1. 🔑 Core Authentication

- **BOT_TOKEN** - Telegram bot token from @BotFather
- **SMSPOOL_API_KEY** - API key from smspool.net
- **ADMIN_IDS** - Comma-separated admin user IDs
- **BINANCE_WALLET** - Crypto wallet for deposits

### 2. 📱 Services Management

Configure which SMS services to offer:

| Service  | ID   | Default Status |    Priority |
| -------- | ---- | -------------: | ----------: |
| Ring4    | 1574 |     ✅ Enabled | 1 (Highest) |
| Telegram | 22   |     ✅ Enabled |           2 |
| Google   | 395  |     ✅ Enabled |           3 |
| WhatsApp | 1012 |     ✅ Enabled |  4 (Lowest) |

**Customizable Settings:**

- Enable/disable individual services
- Set service priorities (order of attempts)
- Customize display names and descriptions
- Configure service-specific settings

### 3. 💰 Pricing Configuration

#### Dynamic Pricing Mode

- **PROFIT_MARGIN_PERCENT** - Global profit margin (default: 5%)
- **MIN_PRICE_USD** - Minimum selling price (default: $0.15)
- **MAX_PRICE_USD** - Maximum selling price (default: $1.00)
- Service-specific margins override global setting

#### Fixed Pricing Mode

- **USE_FIXED_PRICING=true** - Enable fixed pricing
- Set exact prices for each service
- No API price fluctuations

**Example Configuration:**

```env
# Dynamic pricing
PROFIT_MARGIN_PERCENT=5.0
MIN_PRICE_USD=0.15
MAX_PRICE_USD=1.00

# Or fixed pricing
USE_FIXED_PRICING=true
RING4_FIXED_PRICE=0.17
TELEGRAM_FIXED_PRICE=0.25
```

### 4. 🏦 Wallet System

- **MIN_DEPOSIT_USD** - Minimum deposit amount (default: $5.00)
- **MAX_DEPOSIT_USD** - Maximum deposit amount (default: $1000.00)
- **AUTO_APPROVE_BELOW_USD** - Auto-approve small deposits (default: disabled)
- **ENABLE_WALLET_SYSTEM** - Enable/disable wallet functionality

### 5. 🔄 OTP Polling

Fine-tune message delivery speed:

| Setting                   | Default | Description          |
| ------------------------- | ------- | -------------------- |
| POLL_TIMEOUT              | 600s    | Total polling time   |
| POLLING_INITIAL_INTERVAL  | 2s      | First minute speed   |
| POLLING_ACTIVE_INTERVAL   | 3s      | Active polling speed |
| POLLING_STANDARD_INTERVAL | 5s      | Standard speed       |
| POLLING_EXTENDED_INTERVAL | 10s     | Final phase speed    |

### 6. 📋 Business Rules

- **MAX_ORDERS_PER_USER_PER_DAY** - Daily order limit per user
- **MAX_ORDERS_PER_USER_PER_HOUR** - Hourly order limit per user
- **AUTO_REFUND_TIMEOUT** - Auto-refund timeout orders
- **AUTO_REFUND_ERRORS** - Auto-refund error orders

### 7. 🔔 Notifications

Control admin notifications:

- New orders
- Failed orders
- Deposit requests
- Refund requests
- Daily revenue reports

### 8. 🔒 Security Settings

- **RATE_LIMIT_PER_MINUTE** - Requests per minute per user
- **AUTO_BLOCK_SUSPICIOUS** - Auto-block suspicious behavior
- **LARGE_DEPOSIT_THRESHOLD** - Require verification above amount
- **ENABLE_IP_LOGGING** - Log user IP addresses

### 9. ⚙️ Technical Settings

- **ENVIRONMENT** - production/development mode
- **LOG_LEVEL** - DEBUG/INFO/WARNING/ERROR
- **DATABASE_PATH** - Database file location
- **ALLOW_MOCK** - Enable mock mode for testing

### 10. 🚧 Maintenance

- **MAINTENANCE_MODE** - Enable/disable maintenance mode
- **MAINTENANCE_MESSAGE** - Custom maintenance message

## 🎯 Common Configuration Tasks

### Adding a New Service

1. Run `python3 config_manager.py`
2. Choose "2. Manage Services"
3. Choose "1. Enable/Disable services"
4. Enable the desired service
5. Set priority and customize settings

### Changing Pricing Strategy

1. Run `python3 config_manager.py`
2. Choose "3. Configure Pricing"
3. Choose "1. Switch pricing mode"
4. Configure margins or fixed prices

### Setting Up Admin Notifications

1. Run `python3 config_manager.py`
2. Choose "4. Business Rules"
3. Choose "Notifications"
4. Configure desired notification types

### Enabling Maintenance Mode

1. Run `python3 config_manager.py`
2. Choose "5. Technical Settings"
3. Choose "5. Maintenance Mode"
4. Enable and set custom message

## 🔄 Configuration Validation

The system automatically validates:

- ✅ Required fields are present
- ✅ Admin IDs are configured
- ✅ At least one service is enabled
- ✅ Pricing ranges are logical
- ✅ Deposit limits are reasonable

**Validate anytime:**

```bash
python3 config_manager.py
# Choose option 6: Validate Configuration
```

## 💾 Backup & Restore

### Automatic Backups

- Created before major changes
- Named with timestamps
- Stored in `config_backups/` directory

### Manual Backup/Restore

```bash
python3 config_manager.py
# Choose option 7: Backup & Restore
# - Create manual backup
# - Restore from any backup
# - Delete old backups
```

## 📊 Configuration Export

Export current configuration summary:

```bash
python3 config_manager.py
# Choose option 9: Export Configuration Summary
# Creates JSON file with current settings
```

## 🔧 Advanced Configuration

### Environment Variables Hierarchy

1. **config.env** (highest priority)
2. **.env** (fallback)
3. **System environment variables**
4. **Default values** (lowest priority)

### Hot-Reload Configuration

The configuration system supports hot-reloading:

```python
# In your code
config_manager.reload_config()
```

### Service Selection Algorithm

Configure how services are selected:

```env
# Options: weighted, round_robin, price_based
SERVICE_SELECTION_ALGORITHM=weighted
```

### Dynamic Pricing

Enable demand-based pricing adjustments:

```env
ENABLE_DYNAMIC_PRICING=true
DYNAMIC_PRICING_FACTOR=10.0
```

## 🚨 Troubleshooting

### Configuration Not Loading

1. Check file permissions on `config.env`
2. Validate syntax (no spaces around `=`)
3. Run validation tool
4. Check logs for specific errors

### Services Not Working

1. Verify API keys are correct
2. Check service enablement settings
3. Validate service IDs
4. Test API connectivity

### Pricing Issues

1. Check profit margin settings
2. Verify min/max price limits
3. Test with different pricing modes
4. Validate service-specific margins

## 📈 Best Practices

### Security

- Keep API keys secure
- Regularly rotate credentials
- Use strong admin verification
- Enable rate limiting

### Performance

- Monitor polling intervals
- Adjust API timeouts
- Enable performance monitoring
- Optimize database settings

### Business Operations

- Set reasonable order limits
- Configure appropriate margins
- Enable relevant notifications
- Regular backup configurations

## 🆕 Migration from Old System

If upgrading from the old configuration system:

1. **Backup existing `.env`**
2. **Run setup wizard** to create `config.env`
3. **Transfer settings** from old to new format
4. **Validate configuration**
5. **Test functionality**

The new system is backward compatible with the old `.env` file.

## 📞 Support

For configuration help:

1. **Use validation tool** - identifies common issues
2. **Check logs** - detailed error messages
3. **Restore backup** - if configuration breaks
4. **Contact admin** - for complex issues

---

_This configuration system makes the bot accessible to non-technical users while providing advanced options for power users. No coding required!_
