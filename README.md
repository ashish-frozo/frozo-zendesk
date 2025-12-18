# EscalateSafe

**PII-Safe Zendesk → Jira Escalation System**

EscalateSafe prevents PII leakage during support escalations by sanitizing Zendesk tickets (text + images + PDFs) before creating Jira issues and Slack notifications.

## Features

- 🔒 **PII Redaction:** Rules-based detection (Presidio + custom patterns) for emails, phones, API keys, credit cards
- 🖼️ **Image Sanitization:** OCR + masking (Tesseract/Cloud Vision hybrid)
- 📄 **PDF Redaction:** Text-layer + scanned PDF support via PyMuPDF
- 🤖 **LLM Engineering Packs:** Structured bug reports using OpenAI GPT-4 (sanitized-only input)
- ✅ **Approval Gate:** Preview before export, always
- 📊 **Audit Trail:** Full logging for compliance
- 🔐 **Tenant Isolation:** Multi-tenant with strict data separation

## Architecture

```
┌─────────────────┐
│  Zendesk App    │  (React + ZAF SDK)
│   (Sidebar)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────┐
│  FastAPI        │◀─────▶│  PostgreSQL  │
│  Backend        │       └──────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────┐
│  Celery Workers │◀─────▶│    Redis     │
│  (OCR, Redact)  │       └──────────────┘
└─────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Integrations                           │
│  • Zendesk API                          │
│  • Jira Cloud                           │
│  • Slack Webhooks                       │
│  • OpenAI (LLM)                         │
│  • Google Cloud Vision (OCR fallback)   │
│  • S3-compatible storage (MinIO/S3/R2)  │
└─────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15
- Redis 7

### 1. Clone and Setup

```bash
cd /Users/ashishdhiman/WORK/Frozo-projects/frozo-zendesk

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - OpenAI API key
# - Zendesk OAuth credentials
# - Jira API token
# - Slack webhook URL
```

### 2. Start Infrastructure

```bash
# Start PostgreSQL, Redis, MinIO
docker-compose up -d

# Verify services
docker-compose ps
```

### 3. Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (for Presidio)
python -m spacy download en_core_web_lg

# Run database migrations (auto-creates tables for now)
python -m api.main
```

### 4. Start Backend

```bash
# Development mode with hot reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Or using the script
python api/main.py
```

API will be available at: http://localhost:8000
Docs: http://localhost:8000/docs

### 5. Start Celery Worker

```bash
# In a new terminal
celery -A worker.celery_app worker --loglevel=info
```

### 6. Zendesk App Setup

```bash
cd zendesk-app

# Install dependencies
npm install

# Development mode
npm run dev

# Build for production
npm run build

# Validate app structure
npm run validate
```

## Project Structure

```
frozo-zendesk/
├── api/                    # FastAPI backend
│   ├── db/
│   │   ├── models.py       # SQLAlchemy models
│   │   └── database.py     # DB connection
│   ├── routes/             # API endpoints
│   ├── services/
│   │   ├── redaction/      # PII detection & redaction
│   │   └── integrations/   # Zendesk, Jira, Slack
│   ├── middleware/         # Tenant isolation
│   ├── schemas/            # Pydantic models
│   ├── config.py           # Settings
│   └── main.py             # FastAPI app
├── worker/                 # Celery tasks
│   └── tasks/
│       ├── ocr_image.py
│       ├── redact_pdf.py
│       ├── generate_llm_pack.py
│       ├── export_jira.py
│       └── post_slack.py
├── zendesk-app/            # React ZAF app
│   ├── src/
│   │   ├── App.tsx
│   │   └── components/
│   └── manifest.json
├── tests/                  # Testing
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Configuration

See [`.env.example`](./.env.example) for all available configuration options.

### Key Settings

- **Internal Notes:** Default OFF, opt-in at tenant level
- **PDF Limits:** 10 pages max, 10MB max
- **Last Public Comments:** Default 1 (configurable)
- **OCR:** Tesseract first, Cloud Vision fallback
- **Storage:** S3-compatible (MinIO local, S3/R2 production)

## Development Status

**Current Milestone:** M0 - Foundation ✅
- [x] Project structure
- [x] Docker Compose setup
- [x] Database models
- [x] FastAPI backend skeleton
- [x] Zendesk app scaffold
- [x] Zendesk integration service

**Next:** M1 - PII Redaction (Week 2)

See [`task.md`](./task.md) for complete implementation checklist.

## Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# E2E tests
pytest tests/e2e/ -v

# Leak prevention tests (must pass before pilot)
python tests/leak_prevention_test.py --dataset tests/fixtures/synthetic_dataset/
```

## License

Proprietary - Frozo Projects

## Support

For issues or questions, contact: support@frozo.com
