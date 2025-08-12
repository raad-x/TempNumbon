<div align="center">

# Ring4 SMS Verification Bot

High‑reliability Telegram bot for purchasing temporary US (Ring4 + fallback) verification numbers with adaptive OTP polling, dynamic pricing, auditable wallet, and full admin oversight.

**Production Ready · Asynchronous · Wallet Driven · Observable**

</div>

---

## Table of Contents

1. Overview
2. Feature Matrix
3. Architecture & File Layout
4. Data Model
5. Pricing Engine
6. Quick Start
7. Configuration (.env)
8. Commands (User & Admin)
9. Wallet & Order Lifecycle
10. Deployment (systemd)
11. Monitoring & KPIs
12. Security & Integrity
13. Troubleshooting
14. Development & Extensibility
15. Maintenance Cadence
16. Changelog & Roadmap
17. License & Credits
18. Operational Appendix (Scripts & Queries)

---

## 1. Overview

The bot automates temporary US virtual number provisioning (Ring4 primary, with fallback services) and OTP delivery. Users fund a wallet once, spend instantly, and receive codes in near real time. Admins manage deposits, refunds, pricing guardrails, and service health fully inside Telegram.

---

## 2. Feature Matrix

| Category            | Highlights                                                               |
| ------------------- | ------------------------------------------------------------------------ |
| Number Provisioning | Ring4 focus (Service ID 1574) + Telegram / Google / WhatsApp fallbacks   |
| OTP Handling        | Adaptive polling (2s → 3s → 5s → 10s) with timeout + auto refund         |
| Wallet System       | Min deposit configurable, ledger (deposits / spends / refunds)           |
| Admin Operations    | /admin dashboard, deposit approval, refund controls, live services       |
| Pricing             | Dynamic (bounded: MIN ≤ cost\*(1+margin%) ≤ MAX) + per‑service overrides |
| Reliability         | Graceful API retries, structured logs, task cleanup                      |
| Storage             | TinyDB JSON + timestamped backups                                        |
| Security            | Admin allowlist, input validation, secrets in .env                       |
| Observability       | Component loggers, KPIs, grep-friendly markers                           |
| Extensibility       | Modular pricing hook, provider abstraction ready                         |

---

## 3. Architecture & File Layout

```
MNS-SMS(project-root)/
├── main.py                # Bot runtime: handlers, orchestration, polling
├── src/
│   ├── smspool_api.py     # SMSPool API client (pricing, orders, status, cancellation)
│   ├── wallet_system.py   # Wallet + deposits + transactions + refunds
│   ├── order_manager.py   # Order lifecycle coordination
│   └── config.py          # Configuration loaders + pricing helpers
├── data/                  # TinyDB JSON + archived backups
├── logs/                  # ring4_bot.log + auxiliary logs
├── requirements.txt
├── setup_production.sh    # Bootstrap script
└── start_bot.sh           # Lightweight launcher
```

Key runtime concerns:

- Async tasks: OTP polling per order with adaptive backoff
- Separation of concerns: API layer vs wallet vs order orchestration
- Resilience: retry segments (network / upstream) isolated

---

## 4. Data Model (TinyDB Tables)

| Table        | Purpose                   | Core Fields (excerpt)                                                                             |
| ------------ | ------------------------- | ------------------------------------------------------------------------------------------------- |
| orders       | Track number orders & OTP | order_id, user_id, service_id, number, status, cost, created_at, expires_at, otp, otp_received_at |
| refunds      | Manual refund workflow    | refund_id, order_id, user_id, status, processed_by, created_at, processed_at                      |
| wallets      | User wallet profile       | user_id, balance, total_deposited, total_spent, total_refunded, created_at, updated_at            |
| transactions | Immutable ledger          | tx_id, user_id, type (deposit/spend/refund), amount, ref_id, created_at, status                   |
| deposits     | Pending deposit claims    | deposit_id, user_id, amount, status (pending/approved/rejected), created_at, approved_at          |

Status enums (orders): pending | completed | timeout | refunded | cancelled | error

---

## 5. Pricing Engine

Formula:

```
final = max(MIN_PRICE, min(MAX_PRICE, api_cost * (1 + margin%)))
```

Default bounds:

- PROFIT_MARGIN_PERCENT = 5.0
- MIN_PRICE_USD = 0.15
- MAX_PRICE_USD = 1.00

Per‑service override example (config.py):

```python
custom = {1574: 8.0, 22: 5.0, 395: 6.0, 1012: 7.0}
margin = custom.get(service_id, PROFIT_MARGIN_PERCENT)
```

---

## 6. Quick Start

```bash
git clone <repository-url>
cd MNS-SMS(project-root)
chmod +x setup_production.sh
./setup_production.sh      # Creates .env template, dirs, installs deps
nano .env                  # Fill tokens / API key / admin IDs
python3 main.py
```

Online when Telegram getMe succeeds.

---

## 7. Configuration (.env)

Required:
| Variable | Description |
|----------|-------------|
| BOT_TOKEN | Telegram bot token |
| SMSPOOL_API_KEY | SMSPool API key |
| ADMIN_IDS | Comma list of admin user IDs |
| BINANCE_WALLET | Deposit destination address |

Optional:
| Variable | Purpose |
|----------|---------|
| PROFIT_MARGIN_PERCENT / MIN_PRICE_USD / MAX_PRICE_USD | Pricing controls |
| ENVIRONMENT=production|development | Mode toggles |
| LOG_LEVEL=DEBUG|INFO|WARNING | Verbosity |
| ALLOW_MOCK=true|false | Mock fallback |
| DATABASE_PATH | Override TinyDB path |
| TELEGRAM_BOT_TOKEN / PROVIDER_API_KEY / ADMIN_USER_IDS | Alternate variable names |

Restart after changes.

---

## 8. Commands

User:
| Command | Purpose |
|----------|---------|
| /start | Main menu + balance |
| /buy | Purchase (Ring4 default) |
| /balance | Wallet summary |
| /refund | Initiate refund request (eligible orders) |
| /help | Quick help |

Admin:
| Command | Purpose |
|---------|---------|
| /admin | Dashboard: orders, deposits, refunds, stats |
| /approve_refund <order_id> | Approve pending refund |
| /services | Live pricing & availability |

---

## 9. Wallet & Order Lifecycle

| Stage         | Trigger / Event               | Outcome                         |
| ------------- | ----------------------------- | ------------------------------- |
| Deposit Claim | User enters amount            | Record created, admins notified |
| Approval      | Admin validates payment       | Wallet credited, ledger entry   |
| Purchase      | User selects service          | Balance debited, order created  |
| OTP Polling   | After purchase                | Adaptive poll intervals start   |
| Completion    | OTP received                  | Order completed                 |
| Timeout       | No OTP (10m)                  | Auto refund (policy)            |
| Manual Refund | User request + admin approval | Wallet re-credit                |
| Cancellation  | Admin or system error         | Conditional refund              |

Polling schedule (default):

- 0–60s: every 2s
- 61–180s: every 3s
- 181–300s: every 5s
- > 300s to 600s timeout: every 10s

---

## 10. Deployment (systemd)

Service file (/etc/systemd/system/ring4-bot.service):

```ini
[Unit]
Description=Ring4 SMS Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/<user>/ring4-bot
Environment=PATH=/home/<user>/ring4-bot/venv/bin
ExecStart=/home/<user>/ring4-bot/venv/bin/python main.py
Restart=always
RestartSec=8

[Install]
WantedBy=multi-user.target
```

Commands:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ring4-bot
sudo journalctl -u ring4-bot -f
```

---

## 11. Monitoring & KPIs

| Metric             | Target | Source            |
| ------------------ | ------ | ----------------- |
| Order success rate | >95%   | logs              |
| Avg OTP delivery   | <60s   | logs              |
| Refund rate        | <5%    | orders vs refunds |
| API uptime         | >99%   | /services output  |

Quick grep:

```bash
tail -f logs/ring4_bot.log
grep -E "ERROR|CRITICAL" logs/ring4_bot.log | tail -20
grep "completed" logs/ring4_bot.log | wc -l
```

---

## 12. Security & Integrity

| Layer        | Control                               |
| ------------ | ------------------------------------- |
| Secrets      | .env (excluded from VCS)              |
| Admin Access | ID allowlist                          |
| Input        | Validation (amount ranges, IDs)       |
| Refunds      | Manual approval (non-automatic cases) |
| Data         | JSON backups (timestamped)            |
| Logging      | Avoids sensitive payload leakage      |

Backup:

```bash
cp data/ring4_database.json data/backup_$(date +%Y%m%d_%H%M%S).json
```

---

## 13. Troubleshooting

| Issue          | Check                      | Fix                                |
| -------------- | -------------------------- | ---------------------------------- |
| Bot silent     | Telegram getMe             | Validate BOT_TOKEN                 |
| No services    | /services output           | Verify API key / network           |
| OTP delays     | Polling log timestamps     | Adjust intervals / inspect latency |
| Deposits stuck | deposits table status      | Admin oversight workflow           |
| High timeouts  | Ring4 service availability | Use fallback services              |

Diagnostics:

```bash
curl -s https://api.telegram.org/bot$BOT_TOKEN/getMe
curl -s "https://api.smspool.net/request/balance?key=$SMSPOOL_API_KEY"
python3 - <<'PY'
from tinydb import TinyDB
db = TinyDB('data/ring4_database.json')
print('Orders:', len(db.table('orders')))
PY
```

---

## 14. Development & Extensibility

Focus areas:
| Area | Idea |
|------|------|
| Analytics | Daily/weekly revenue aggregation |
| I18n | Language packs |
| Rate limiting | Per-user adaptive throttling |
| Metrics | Prometheus / OTel exporter |
| Providers | Multi-vendor abstraction |

Debug:

```bash
LOG_LEVEL=DEBUG ENVIRONMENT=development python3 main.py
```

Extend pricing (time-based, per-service) via config.py hook.

---

## 15. Maintenance Cadence

| Frequency | Tasks                                                      |
| --------- | ---------------------------------------------------------- |
| Daily     | Review logs, approve deposits, process refunds             |
| Weekly    | DB backup, pricing sanity, error trend review              |
| Monthly   | Dependency updates, archive aged orders, performance audit |

Health snippet:

```bash
pgrep -f "python.*main.py" >/dev/null && echo OK || echo DOWN
du -h logs/ring4_bot.log 2>/dev/null | cut -f1
grep -c "ERROR" logs/ring4_bot.log || true
```

---

## 16. Changelog & Roadmap

v1.0.0

- Initial production release (wallet, adaptive polling, admin dashboard, dynamic pricing, refunds, structured logging)

Roadmap

- Auto-tuning polling strategy
- Advanced profit analytics
- Multi-language UX
- Multi-provider redundancy layer
- Anti-abuse heuristics / rate limiting

---

## 17. License & Credits

License: Proprietary – all rights reserved.

Credits:

- python-telegram-bot
- aiohttp
- tinydb
- python-dotenv
- psutil
- SMSPool API

---

## 18. Operational Appendix

### Service Status Check

```bash
/systemctl status ring4-bot
curl -s "https://api.smspool.net/request/balance?key=$SMSPOOL_API_KEY"
```

### Revenue (Last 7 Days) Example

```bash
python3 - <<'PY'
from tinydb import TinyDB
from datetime import datetime, timedelta
db = TinyDB('data/ring4_database.json')
orders = db.table('orders')
cut = datetime.utcnow() - timedelta(days=7)
import iso8601 as _p  # if available else parse manually
def p(ts):
    from datetime import datetime
    return datetime.fromisoformat(ts)
recent = [o for o in orders if p(o['created_at']) > cut and o['status']=="completed"]
rev = sum(float(o.get('cost',0)) for o in recent)
print(f"Completed: {len(recent)}  Revenue: ${rev:.2f}")
PY
```

### Pricing Adjust

```bash
nano .env
# Adjust PROFIT_MARGIN_PERCENT / MIN_PRICE_USD / MAX_PRICE_USD
systemctl restart ring4-bot
```

### Manual Backup & Archive

```bash
cp data/ring4_database.json data/backup_$(date +%Y%m%d_%H%M%S).json
```

---

### Quick Reference

| Action         | Command / Step                                               |
| -------------- | ------------------------------------------------------------ |
| Start bot      | python3 main.py                                              |
| Show services  | /services (admin)                                            |
| Approve refund | /approve_refund <order_id>                                   |
| Check wallet   | /balance                                                     |
| Adjust pricing | Edit .env → restart                                          |
| Backup DB      | cp data/ring4*database.json data/backup*$(date +%Y%m%d).json |

---

**Production Ready • Observable • Extensible**
