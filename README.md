# Baron Kitchen — Order Management System

A fully working Python prototype for centralized, multi-channel order management.

## Project Structure

```
baron_oms/
├── app.py                   ← Flask app + REST API + dashboard
├── demo.py                  ← Demo data seeder
├── requirements.txt
├── models/
│   ├── order.py             ← Order, OrderItem, enums
│   └── store.py             ← In-memory order store (swap for Postgres)
├── channels/
│   └── intake.py            ← Phone / WhatsApp / Email / Website adapters
├── services/
│   ├── ai_extractor.py      ← AI + rule-based order extraction
│   ├── alerts.py            ← Fail-safes, watchdog, alert log
│   └── zoho.py              ← Zoho CRM + Books integration
└── tests/
    └── test_oms.py          ← Unit tests (pytest)
```

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py

# 4. Open dashboard
# → http://localhost:5000

# 5. Load demo data
# Click "Load Demo Data" on the dashboard, OR:
curl -X POST http://localhost:5000/api/demo/seed

# 6. Run tests
python -m pytest tests/ -v
```

## Enable Live AI Extraction (Optional)

Set one of these environment variables before running:

```bash
# OpenAI (recommended)
export OPENAI_API_KEY="sk-..."

# OR Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant-..."
```

Without an API key, the system uses a rule-based regex parser (still functional).

## Enable Zoho Integration (Optional)

```bash
export ZOHO_CLIENT_ID="your_client_id"
export ZOHO_CLIENT_SECRET="your_client_secret"
export ZOHO_REFRESH_TOKEN="your_refresh_token"
export ZOHO_ORG_ID="your_org_id"
```

Without credentials, Zoho calls are simulated and logged to console.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Live dashboard |
| GET | `/api/orders` | All orders |
| GET | `/api/orders/<id>` | Single order |
| POST | `/api/intake/phone` | Submit call transcript |
| POST | `/api/intake/whatsapp` | Submit WhatsApp message |
| POST | `/api/intake/email` | Submit email |
| POST | `/api/intake/website` | Submit website order (JSON) |
| POST | `/api/orders/confirm/<id>` | Confirm a draft order |
| POST | `/api/orders/status/<id>` | Update order status |
| POST | `/api/orders/dispatch/<id>` | Dispatch + auto-invoice |
| GET | `/api/alerts` | Alert log |
| GET | `/api/stats` | Dashboard stats |
| POST | `/api/demo/seed` | Load demo data |

## Production Upgrades

| Component | Current (Prototype) | Production |
|-----------|--------------------|--------------------|
| Database | In-memory dict | PostgreSQL + SQLAlchemy |
| Alerts | Console print | Twilio SMS + Slack webhook |
| Phone intake | Manual transcript | Twilio webhook + Whisper STT |
| WhatsApp | Manual message | WhatsApp Business API webhook |
| Email | Manual input | Nylas / Zapier webhook |
| Auth | None | JWT + role-based access |
| Deployment | Flask dev server | Gunicorn + Docker + AWS |
