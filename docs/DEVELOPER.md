# Developer Guide

Technical architecture and development guide for EscalateSafe contributors.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Development Setup](#development-setup)
4. [Code Organization](#code-organization)
5. [Key Components](#key-components)
6. [Database Schema](#database-schema)
7. [Testing](#testing)
8. [Contributing](#contributing)

---

## Architecture Overview

### High-Level Design

```
┌────────────────────────────────────────────────────┐
│                 Zendesk Frontend                   │
│  ┌──────────────┐  ┌──────────────┐               │
│  │ Ticket       │  │ Top Bar      │               │
│  │ Sidebar      │  │ (Install)    │               │
│  │              │  │              │               │
│  │ - Main UI    │  │ - OAuth Flow │               │
│  │ - Settings   │  │ - Welcome    │               │
│  │ - Preview    │  │              │               │
│  └──────┬───────┘  └──────┬───────┘               │
│         │                  │                        │
│         └────────┬─────────┘                        │
│                  │ ZAF SDK + OAuth Headers         │
└──────────────────┼────────────────────────────────┘
                   │ HTTPS/REST API
┌──────────────────▼────────────────────────────────┐
│               FastAPI Backend                      │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │           Route Layer                        │ │
│  │  /oauth, /config, /runs, /health             │ │
│  └─────────────┬────────────────────────────────┘ │
│                │                                   │
│  ┌─────────────▼────────────────────────────────┐ │
│  │         Service Layer                        │ │
│  │  - OAuth Service (token mgmt)                │ │
│  │  - Config Service (settings)                 │ │
│  │  - PII Detector (Presidio + spaCy)           │ │
│  │  - Redactor (text anonymization)             │ │
│  │  - Zendesk Service (API client)              │ │
│  │  - Jira Service (issue creation)             │ │
│  │  - Slack Service (notifications)             │ │
│  └─────────────┬────────────────────────────────┘ │
│                │                                   │
│  ┌─────────────▼────────────────────────────────┐ │
│  │          Data Layer (SQLAlchemy)             │ │
│  │  Models: Tenant, Run, Export, AuditEvent     │ │
│  └─────────────┬────────────────────────────────┘ │
└────────────────┼──────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│            PostgreSQL Database                  │
│  - Tenants & OAuth tokens (encrypted)          │
│  - Runs & escalations                          │
│  - Configuration                                │
│  - Audit logs                                  │
└───────────────────────────────────────────────────┘
```

### Tech Stack

**Backend:**
- **Framework:** FastAPI 0.104+
- **ORM:** SQLAlchemy 2.0
- **Database:** PostgreSQL 14+
- **PII Detection:** Microsoft Presidio 2.2
- **NLP:** spaCy 3.7 (en_core_web_lg)
- **Integrations:** Zenpy, Jira, Requests

**Frontend:**
- **Platform:** Zendesk App Framework 2.0
- **Language:** Vanilla JavaScript (ES6+)
- **Auth:** OAuth 2.0
- **Build:** Custom packaging script

**Infrastructure:**
- **Hosting:** Railway (recommended)
- **Database:** Railway PostgreSQL
- **Environment:** Python 3.11+

---

## Project Structure

```
frozo-zendesk/
├── api/                          # Backend API
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry
│   ├── config.py                 # Settings (Pydantic)
│   │
│   ├── db/                       # Database layer
│   │   ├── database.py           # SQLAlchemy setup
│   │   ├── models.py             # ORM models
│   │   └── migrations/           # SQL migrations
│   │       ├── 001_initial_schema.sql
│   │       ├── 002_add_audit_log.sql
│   │       └── 003_add_oauth_to_tenants.sql
│   │
│   ├── routes/                   # API endpoints
│   │   ├── __init__.py
│   │   ├── oauth.py              # OAuth flow
│   │   ├── config.py             # Settings CRUD
│   │   ├── runs.py               # Escalation mgmt
│   │   └── health.py             # Health checks
│   │
│   ├── services/                 # Business logic
│   │   ├── oauth_service.py      # Token management
│   │   ├── config_service.py     # Config operations
│   │   ├── integrations/         # External APIs
│   │   │   ├── zendesk.py        # Zendesk client
│   │   │   ├── zendesk_oauth.py  # OAuth helper
│   │   │   ├── jira.py           # Jira client
│   │   │   └── slack.py          # Slack webhooks
│   │   └── redaction/            # PII processing
│   │       ├── detector.py       # Presidio wrapper
│   │       └── text_redactor.py  # Redaction engine
│   │
│   ├── schemas/                  # Pydantic models
│   │   ├── runs.py               # Run DTOs
│   │   └── config.py             # Config DTOs
│   │
│   └── utils/                    # Utilities
│       └── encryption.py         # Token encryption
│
├── zendesk-app/                  # Frontend app
│   ├── manifest.json             # App configuration
│   ├── package-app.sh            # Build script
│   │
│   ├── assets/                   # Static files
│   │   ├── index.html            # Main UI
│   │   ├── install.html          # OAuth install
│   │   ├── oauth-success.html    # Post-OAuth
│   │   ├── settings.html         # Legacy settings
│   │   ├── logo.png              # App icon
│   │   └── logo.svg              # Vector logo
│   │
│   └── translations/             # i18n
│       └── en.json               # English strings
│
├── docs/                         # Documentation
│   ├── INSTALLATION.md
│   ├── USER_GUIDE.md
│   ├── DEVELOPER.md              # This file
│   ├── API.md
│   ├── SECURITY.md
│   └── MARKETPLACE.md
│
├── tests/                        # Test suite
│   └── test_m1_redaction.py
│
├── requirements.txt              # Python deps
├── runtime.txt                   # Python version
├── Procfile                      # Process config
├── railway.toml                  # Railway config
└── README.md                     # Project overview
```

---

## Development Setup

### Prerequisites

```bash
# Python 3.11+
python --version

# PostgreSQL 14+
psql --version

# Node.js (for tooling)
node --version
```

### Local Backend Setup

**1. Clone repository**
```bash
git clone https://github.com/your-org/frozo-zendesk
cd frozo-zendesk
```

**2. Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_lg
```

**4. Set up database**
```bash
# Create PostgreSQL database
createdb escalatesafe_dev

# Set environment variable
export DATABASE_URL="postgresql://localhost/escalatesafe_dev"
```

**5. Run migrations**
```bash
python -c "from api.db.database import Base, engine; Base.metadata.create_all(bind=engine)"

# Or run SQL files manually
psql $DATABASE_URL < api/db/migrations/001_initial_schema.sql
psql $DATABASE_URL < api/db/migrations/002_add_audit_log.sql
psql $DATABASE_URL < api/db/migrations/003_add_oauth_to_tenants.sql
```

**6. Create `.env` file**
```bash
# .env
DATABASE_URL=postgresql://localhost/escalatesafe_dev
ENCRYPTION_KEY=$(openssl rand -hex 32)
ZENDESK_CLIENT_ID=test_client_id
ZENDESK_CLIENT_SECRET=test_secret
API_BASE_URL=http://localhost:8080
ZENDESK_EMAIL=test@example.com
ZENDESK_API_TOKEN=test_token
ZENDESK_SUBDOMAIN=test
```

**7. Run development server**
```bash
uvicorn api.main:app --reload --port 8080

# Server starts at http://localhost:8080
# API docs at http://localhost:8080/docs
```

### Frontend Development

**1. Install Zendesk CLI (ZCLI)**
```bash
npm install -g @zendesk/zcli
```

**2. Package app**
```bash
cd zendesk-app
./package-app.sh
```

**3. Test locally**
```bash
# Serve app locally
zcli apps:server

# Access at: https://yoursubdomain.zendesk.com/agent/tickets/1?zcli_apps=true
```

**4. Upload to Zendesk**
```bash
# Upload the generated ZIP
# Go to Zendesk Admin → Apps → Upload private app
```

---

## Code Organization

### Backend Patterns

**1. Route → Service → Model**
```python
# routes/runs.py
@router.post("/")
async def create_run(request: RunCreateRequest, db: Session = Depends(get_db)):
    # Minimal logic - delegate to service
    tenant = get_tenant(db, subdomain)
    zendesk_client = get_zendesk_client_for_tenant(tenant, db)
    
    # Service handles business logic
    detector = create_detector()
    results = detector.analyze(text)
    
    # Model persistence
    run = Run(...)
    db.add(run)
    db.commit()
```

**2. Dependency Injection**
```python
# Use FastAPI dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# In routes
async def endpoint(db: Session = Depends(get_db)):
    ...
```

**3. Error Handling**
```python
# Raise HTTP exceptions
if not tenant:
    raise HTTPException(status_code=404, detail="Tenant not found")

# Log errors
logger.error(f"Failed to process: {e}")
```

### Frontend Patterns

**1. ZAF Client Wrapper**
```javascript
const client = ZAFClient.init();

// Get context
const context = await client.context();
const subdomain = context.account.subdomain;

// Metadata for settings
const metadata = await client.metadata();
const apiBaseUrl = metadata.settings.api_base_url;
```

**2. API Call Helper**
```javascript
async function apiCall(endpoint, options = {}) {
    const response = await fetch(`${apiBaseUrl}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'X-Zendesk-Subdomain': subdomain,
            ...options.headers
        }
    });
    return response;
}
```

**3. State Management**
```javascript
// Simple state variables
let ticketId = null;
let runId = null;
let runData = null;

// Update UI based on state
function renderPreview(data) {
    runData = data;
    app.innerHTML = `...`;
}
```

---

## Key Components

### OAuth Service

**File:** `api/services/oauth_service.py`

**Responsibilities:**
- Exchange authorization code for tokens
- Refresh expired tokens
- Store encrypted tokens in database
- Validate token expiry

**Key Methods:**
```python
class ZendeskOAuthService:
    def exchange_code_for_tokens(code, subdomain, redirect_uri)
    def refresh_access_token(tenant)
    def store_tokens(tenant, access_token, refresh_token, expires_in, scope)
    def is_token_expired(tenant)
```

### PII Detector

**File:** `api/services/redaction/detector.py`

**Responsibilities:**
- Initialize Presidio analyzer
- Detect PII entities (email, phone, names, etc.)
- Custom recognizers (API keys, credit cards)
- Confidence scoring

**Key Classes:**
```python
class PIIDetector:
    def __init__(enable_indian_entities, confidence_threshold, entities_to_detect)
    def analyze(text, language="en")
    def get_entity_counts(results)
    def get_low_confidence_entities(results, threshold=0.7)

class APIKeyRecognizer(PatternRecognizer):
    # Detects API keys, tokens, secrets

class CreditCardRecognizer(PatternRecognizer):
    # Detects cards in various formats

class PhoneNumberRecognizer(PatternRecognizer):
    # Detects US/international phones
```

### Zendesk OAuth Helper

**File:** `api/services/integrations/zendesk_oauth.py`

**Responsibilities:**
- Get Zendesk client with valid OAuth token
- Auto-refresh tokens if expired
- Fallback to API token if OAuth not configured

**Usage:**
```python
zendesk_client = await get_zendesk_client_for_tenant(tenant, db)
ticket = zendesk_client.get_ticket(ticket_id)
```

---

## Database Schema

### Tenants Table

```sql
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    zendesk_subdomain VARCHAR(255) UNIQUE NOT NULL,
    
    -- OAuth fields
    oauth_access_token TEXT,                    -- Encrypted
    oauth_refresh_token TEXT,                   -- Encrypted
    oauth_token_expires_at TIMESTAMP,
    oauth_scopes TEXT,
    installation_id VARCHAR(255),
    installation_status VARCHAR(50),
    installed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_subdomain ON tenants(zendesk_subdomain);
CREATE INDEX idx_oauth_expiry ON tenants(oauth_token_expires_at);
```

### Runs Table

```sql
CREATE TABLE runs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    ticket_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    
    redaction_report JSONB,          -- PII stats
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_runs_tenant ON runs(tenant_id);
CREATE INDEX idx_runs_ticket ON runs(ticket_id);
CREATE INDEX idx_runs_status ON runs(status);
```

### Full Schema

See: `api/db/models.py` for complete ORM definitions

---

## Testing

### Unit Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_m1_redaction.py

# With coverage
pytest --cov=api tests/
```

### Integration Tests

```bash
# Test OAuth flow
curl -X POST http://localhost:8080/v1/oauth/install \
  -H "Content-Type: application/json" \
  -d '{"subdomain":"test","app_guid":"abc","locale":"en"}'

# Test PII detection
curl -X POST http://localhost:8080/v1/runs/ \
  -H "Content-Type: application/json" \
  -H "X-Zendesk-Subdomain: test" \
  -d '{"ticket_id":"123"}'
```

### Manual Testing

1. Start local backend
2. Upload app to Zendesk test account
3. Test full flow: Install → Settings → Escalation
4. Check logs for errors
5. Verify database state

---

## Contributing

### Development Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Follow code style (Black, isort)
   - Add tests
   - Update docs

3. **Run tests**
   ```bash
   pytest
   black api/
   isort api/
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat: Add new feature"
   ```

5. **Push & PR**
   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub
   ```

### Code Style

**Python:**
- Use Black formatter
- Follow PEP 8
- Type hints encouraged
- Docstrings for public methods

**JavaScript:**
- ES6+ syntax
- Consistent indentation (2 spaces)
- Comments for complex logic

### Commit Messages

Follow conventional commits:
```
feat: Add phone number recognition
fix: Correct OAuth token refresh
docs: Update installation guide
refactor: Extract helper function
test: Add unit tests for detector
```

---

## Resources

- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Presidio:** https://github.com/microsoft/presidio
- **Zendesk Apps:** https://developer.zendesk.com/apps/
- **Railway:** https://docs.railway.app

---

**Questions?** Open an issue or contact [hello@frozo.ai](mailto:hello@frozo.ai)
