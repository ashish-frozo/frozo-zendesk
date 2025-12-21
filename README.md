# EscalateSafe - PII-Safe Zendesk to Jira Escalation

<div align="center">

🛡️ **Secure Support Ticket Escalation with Automatic PII Redaction**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/ashish-frozo/frozo-zendesk)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Zendesk](https://img.shields.io/badge/Zendesk-Compatible-orange.svg)](https://www.zendesk.com)

[Features](#features) • [Installation](#installation) • [Documentation](#documentation) • [Support](#support)

</div>

---

## 🎯 Overview

**EscalateSafe** is a Zendesk marketplace app that enables secure escalation of support tickets to engineering teams while automatically detecting and redacting personally identifiable information (PII). Perfect for companies that need to share customer issues with engineering without compromising customer privacy.

### The Problem

Support teams often need to escalate customer issues to engineering, but customer tickets contain sensitive information:
- Customer names, emails, phone numbers
- Credit card numbers, API keys
- Personally identifiable information (PII)

Sharing this data with engineering teams violates privacy policies and regulations (GDPR, CCPA, etc.).

### The Solution

EscalateSafe automatically:
1. ✅ **Detects PII** using AI-powered recognition (Microsoft Presidio)
2. ✅ **Redacts sensitive data** before sharing
3. ✅ **Shows preview** for agent review before export
4. ✅ **Creates Jira issues** with sanitized content
5. ✅ **Notifies via Slack** when escalations are created
6. ✅ **Multi-tenant OAuth** - Each customer's data stays isolated

---

## ✨ Features

### 🔒 PII Detection & Redaction

**Automatically detects and redacts:**
- Names (using NLP)
- Email addresses
- Phone numbers (all formats: +1-555-123-4567, (555) 987-6543, etc.)
- Credit cards (all formats: 4532-1234-5678-9012, dashed, spaced)
- API keys and tokens
- Locations and addresses
- Custom patterns (configurable)

**Advanced capabilities:**
- Confidence scoring (adjustable threshold)
- Low-confidence warnings
- Smart deduplication (skips copied comments)
- India-specific entities (PAN, GSTIN) - optional

### 🎯 Jira Integration

- Creates engineering tickets automatically
- Uses sanitized, PII-free content
- Configurable project, issue type, priority
- Clickable links back to Jira issue
- Custom field mapping
- Idempotency (no duplicate issues)

### 📢 Slack Notifications

- Notifies team when escalations created
- Includes Jira link and ticket summary
- Configurable channels
- Rich formatting

### 🛡️ Multi-Tenant OAuth

- Each customer gets own OAuth tokens
- Complete data isolation
- Self-service installation
- Automatic token refresh
- Marketplace-ready

### ⚙️ Settings UI

- In-app configuration (no admin panel needed)
- Jira connection testing
- Slack webhook configuration
- Redaction settings
- Real-time validation

---

## 🚀 Quick Start

### For End Users (Zendesk Agents)

1. **Install the app** from Zendesk Marketplace
2. **Authorize** when prompted (OAuth flow)
3. **Configure** Jira & Slack in Settings
4. **Open a ticket** → See EscalateSafe in sidebar
5. **Click "Generate Pack"** → Review redacted preview
6. **Approve** → Jira issue created automatically!

### For Administrators

See [INSTALLATION.md](docs/INSTALLATION.md) for detailed setup guide.

---

## 📋 Requirements

### Zendesk
- Zendesk Suite or Support Professional plan
- Admin access for app installation
- OAuth permissions

### Jira
- Jira Cloud account
- API token
- Project with appropriate permissions

### Slack (Optional)
- Workspace admin access
- Incoming webhook URL

### Backend (Self-Hosted)
- Python 3.11+
- PostgreSQL 14+
- Railway/Heroku/AWS (or any hosting)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](docs/INSTALLATION.md) | Step-by-step setup instructions |
| [User Guide](docs/USER_GUIDE.md) | How to use the app |
| [Developer Guide](docs/DEVELOPER.md) | Technical architecture & development |
| [API Reference](docs/API.md) | Backend API documentation |
| [Deployment Guide](docs/DEPLOYMENT.md) | Production deployment |
| [Security](docs/SECURITY.md) | Privacy & security details |
| [Marketplace](docs/MARKETPLACE.md) | Submission guide |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│          Zendesk App (Frontend)             │
│  - OAuth installation flow                  │
│  - Ticket sidebar interface                 │
│  - Settings UI                              │
│  - Preview & approval                       │
└──────────────────┬──────────────────────────┘
                   │ HTTPS + OAuth
┌──────────────────▼──────────────────────────┐
│        Backend API (FastAPI)                │
│  - OAuth token management                   │
│  - PII detection (Presidio + spaCy)         │
│  - Redaction engine                         │
│  - Jira integration                         │
│  - Slack notifications                      │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│        PostgreSQL Database                  │
│  - Tenants & OAuth tokens                   │
│  - Runs & escalation history                │
│  - Configuration                            │
│  - Audit logs                               │
└─────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

**Frontend:**
- Zendesk App Framework (ZAF SDK 2.0)
- Vanilla JavaScript
- OAuth 2.0

**Backend:**
- Python 3.11
- FastAPI
- SQLAlchemy
- Presidio (PII detection)
- spaCy (NLP)
- Zenpy (Zendesk API)
- Jira Python SDK

**Database:**
- PostgreSQL 14+
- Encrypted token storage

**Infrastructure:**
- Railway (recommended)
- Heroku, AWS, GCP (also supported)

---

## 🔐 Security & Privacy

- ✅ **OAuth 2.0** - No hardcoded credentials
- ✅ **Encrypted tokens** - AES-256 encryption at rest
- ✅ **HTTPS only** - All API calls over TLS
- ✅ **Tenant isolation** - Complete data separation
- ✅ **No PII storage** - Redacted content only
- ✅ **Audit logs** - Full trail of all escalations
- ✅ **GDPR compliant** - Privacy by design

See [SECURITY.md](docs/SECURITY.md) for complete details.

---

## 📊 Metrics & Analytics

Track your escalations:
- Total escalations created
- PII entities detected
- Redaction statistics
- Export success rate
- OAuth health per tenant

(Dashboard coming soon!)

---

## 🤝 Support

**For Users:**
- Email: [hello@frozo.ai](mailto:hello@frozo.ai)
- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/ashish-frozo/frozo-zendesk/issues)

**For Developers:**
- Developer Guide: [docs/DEVELOPER.md](docs/DEVELOPER.md)
- API Docs: [docs/API.md](docs/API.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- [Microsoft Presidio](https://github.com/microsoft/presidio) - PII detection
- [spaCy](https://spacy.io/) - NLP engine
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Zendesk Apps Framework](https://developer.zendesk.com/apps/) - Platform

---

## 🗺️ Roadmap

**v1.1** (Coming Soon)
- [ ] PDF/Image redaction
- [ ] Custom redaction patterns UI
- [ ] Analytics dashboard
- [ ] Multi-language support

**v1.2** (Planned)
- [ ] ServiceNow integration
- [ ] GitHub Issues export
- [ ] AI-powered categorization
- [ ] Advanced reporting

---

## 📸 Screenshots

### Ticket Sidebar
![Ticket Sidebar](docs/images/sidebar.png)

### PII Detection Preview
![Preview Screen](docs/images/preview.png)

### Settings UI
![Settings](docs/images/settings.png)

### Installation Flow
![Installation](docs/images/install.png)

---

<div align="center">

**Made with ❤️ by [Frozo](https://frozo.ai)**

[Website](https://frozo.ai) • [Twitter](https://twitter.com/frozo_ai) • [LinkedIn](https://linkedin.com/company/frozo)

</div>
