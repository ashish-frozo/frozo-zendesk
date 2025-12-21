# Security & Privacy

Security architecture, privacy policy, and compliance information for EscalateSafe.

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [Data Handling](#data-handling)
3. [Encryption](#encryption)
4. [OAuth Security](#oauth-security)
5. [PII Protection](#pii-protection)
6. [GDPR Compliance](#gdpr-compliance)
7. [Audit Logging](#audit-logging)
8. [Vulnerability Reporting](#vulnerability-reporting)

---

## Security Overview

### Architecture

```
┌─────────────────────────────────────────┐
│         Zendesk (Data Source)           │
│  - Tickets stored in Zendesk            │
│  - OAuth tokens grant access            │
│  - SSL/TLS encryption                   │
└────────────────┬────────────────────────┘
                 │ HTTPS Only
┌────────────────▼────────────────────────┐
│        EscalateSafe Backend             │
│  ┌────────────────────────────────────┐ │
│  │  1. PII Detection (Presidio)       │ │
│  │     - No data stored permanently   │ │
│  │     - In-memory processing         │ │
│  ├────────────────────────────────────┤ │
│  │  2. Redaction Engine               │ │
│  │     - Only redacted text stored    │ │
│  │     - Original never persisted     │ │
│  ├────────────────────────────────────┤ │
│  │  3. Database                       │ │
│  │     - OAuth tokens (encrypted)     │ │
│  │     - Redacted content only        │ │
│  │     - Audit logs                   │ │
│  └────────────────────────────────────┘ │
└────────────────┬────────────────────────┘
                 │ HTTPS Only
┌────────────────▼────────────────────────┐
│          Jira (Destination)             │
│  - Receives redacted content            │
│  - No PII transmitted                   │
│  - SSL/TLS encryption                   │
└─────────────────────────────────────────┘
```

### Security Principles

1. **Privacy by Design** - PII never stored
2. **Zero Trust** - OAuth per tenant
3. **Encryption at Rest** - All secrets encrypted
4. **Encryption in Transit** - HTTPS only
5. **Minimal Retention** - Data deleted after export
6. **Audit Everything** - Complete audit trail

---

## Data Handling

### What We Process

**Temporary (In-Memory Only):**
- ✅ Ticket descriptions
- ✅ Customer comments
- ✅ Detected PII entities
- ✅ Original unredacted text

**Stored (Redacted Only):**
- ✅ Redacted ticket content
- ✅ PII detection statistics
- ✅ Export metadata

**Never Stored:**
- ❌ Customer names
- ❌ Email addresses
- ❌ Phone numbers
- ❌ Credit card numbers
- ❌ API keys
- ❌ Any personally identifiable information

### Data Flow

```
Ticket Fetched
      ↓
Analyzed (Memory)
      ↓
PII Detected
      ↓
Redacted (Memory)
      ↓
Preview Generated
      ↓
Stored in DB: REDACTED TEXT ONLY
      ↓
Exported to Jira
      ↓
Marked as Exported
      ↓
Original Text: NEVER STORED
```

### Data Retention

| Data Type | Retention | Purpose |
|-----------|-----------|---------|
| OAuth tokens | Until revoked | Authentication |
| Redacted content | 30 days | Audit trail |
| Run metadata | 90 days | Analytics |
| Audit logs | 1 year | Compliance |
| Original PII | 0 seconds | Never stored |

### Data Deletion

Users can request deletion of:
- Tenant data
- OAuth tokens
- Audit logs

**Contact:** [hello@frozo.ai](mailto:hello@frozo.ai)

---

## Encryption

### At Rest

**OAuth Tokens:**
```python
from cryptography.fernet import Fernet

# 256-bit AES encryption
cipher = Fernet(encryption_key)
encrypted_token = cipher.encrypt(oauth_token.encode())

# Stored encrypted in database
tenant.oauth_access_token = encrypted_token
```

**Encryption Key:**
- Generated using: `openssl rand -hex 32`
- Stored in environment variables
- Never committed to code
- Rotated annually

**Database:**
- PostgreSQL (Railway)
- Encrypted at rest (provider-level)
- Automatic backups
- Point-in-time recovery

### In Transit

**All API Calls:**
- ✅ HTTPS/TLS 1.2+
- ✅ Certificate validation
- ✅ No mixed content

**Zendesk OAuth:**
- ✅ OAuth 2.0 over HTTPS
- ✅ State parameter for CSRF protection
- ✅ Short-lived authorization codes

**Jira API:**
- ✅ API tokens over HTTPS
- ✅ Bearer authentication
- ✅ Token stored encrypted

---

## OAuth Security

### OAuth 2.0 Flow

```
1. User clicks "Install" in Zendesk Marketplace
         ↓
2. Backend generates authorization URL
   - includes state parameter (CSRF protection)
   - includes redirect_uri (validated by Zendesk)
         ↓
3. User redirected to Zendesk OAuth page
   - Zendesk verifies client_id
   - User grants permissions
         ↓
4. Zendesk redirects to /v1/oauth/callback
   - includes authorization code
   - includes state parameter
         ↓
5. Backend validates state parameter
   - exchanges code for tokens
   - stores tokens (encrypted)
         ↓
6. User can now use app with their OAuth token
```

### Token Management

**Access Tokens:**
- Short-lived (typically 1 hour)
- Stored encrypted in database
- Auto-refreshed before expiry

**Refresh Tokens:**
- Long-lived (can be revoked)
- Stored encrypted in database
- Used to get new access tokens

**Token Refresh:**
```python
if tenant.oauth_token_expires_at < now + timedelta(minutes=5):
    new_tokens = refresh_access_token(tenant)
    store_tokens(tenant, new_tokens)
```

### Security Best Practices

- ✅ State parameter prevents CSRF
- ✅ Redirect URI validated by Zendesk
- ✅ Tokens encrypted at rest
- ✅ Auto-refresh prevents expiry
- ✅ Per-tenant isolation
- ✅ No token sharing between tenants

---

## PII Protection

### Detection Technology

**Microsoft Presidio:**
- Industry-standard PII detection
- AI-powered entity recognition
- Regex pattern matching
- Confidence scoring

**spaCy NLP:**
- Named entity recognition (NER)
- Detects person names, locations
- Pre-trained on large corpus

### Detection Coverage

**Personal Identifiers:**
- ✅ Names (John Doe, Sarah Smith)
- ✅ Email addresses (all formats)
- ✅ Phone numbers (US/international)
- ✅ Social Security Numbers (US)
- ✅ Passport numbers

**Financial Data:**
- ✅ Credit card numbers (all formats)
- ✅ Bank account numbers
- ✅ IBAN codes

**Technical Secrets:**
- ✅ API keys
- ✅ Bearer tokens
- ✅ JWT tokens
- ✅ Hex keys (32+ chars)

**Geographic:**
- ✅ Addresses
- ✅ Locations
- ✅ Postal codes

### Redaction Format

```
Original:  "Contact John Doe at john@example.com or +1-555-123-4567"
Redacted:  "Contact [NAME_REDACTED] at [EMAIL_REDACTED] or [PHONE_NUMBER_REDACTED]"

Original:  "API Key: sk_live_4o4E78gQZ9LhN8..."
Redacted:  "API Key: [API_KEY_REDACTED]"

Original:  "Card: 4532-1234-5678-9012"
Redacted:  "Card: [CREDIT_CARD_REDACTED]"
```

### Confidence Thresholds

| Level | Score | Action |
|-------|-------|--------|
| High | 0.8-1.0 | Always redact |
| Medium | 0.6-0.8 | Redact with confidence |
| Low | 0.5-0.6 | Redact + warning |
| Very Low | <0.5 | Don't redact |

**Low confidence warnings** logged for admin review.

### False Positives

**Minimal by design:**
- Product names: Not redacted (not PII)
- Error codes: Not redacted (technical data)
- Timestamps: Not redacted (system data)

If false positive occurs, contact support to adjust patterns.

---

## GDPR Compliance

### Legal Basis

**Article 6(1)(b):** Processing necessary for contract performance
- Users request escalation service
- PII redaction fulfills privacy obligation

**Article 6(1)(f):** Legitimate interests
- Preventing data leaks
- Protecting customer privacy

### Data Subject Rights

**Right to Access:**
- Users can request all data we hold
- Contact: [hello@frozo.ai](mailto:hello@frozo.ai)

**Right to Erasure:**
- Delete tenant account
- Remove all OAuth tokens
- Purge audit logs

**Right to Portability:**
- Export all tenant data
- Machine-readable format (JSON)

**Right to Restrict Processing:**
- Pause run creation
- Disable exports

### Data Processing Agreement

**Controller:** Your Company (Zendesk account owner)

**Processor:** Frozo (EscalateSafe operator)

**Sub-processors:**
- Railway (hosting)
- PostgreSQL (database)

### Data Protection Measures

- ✅ Encryption at rest and in transit
- ✅ Access controls (OAuth)
- ✅ Audit logging
- ✅ Regular security updates
- ✅ Incident response plan

### Breach Notification

In case of data breach:
1. Notification within 72 hours
2. Email to all affected tenants
3. Details of breach scope
4. Remediation steps

Contact: [security@frozo.ai](mailto:security@frozo.ai)

---

## Audit Logging

### What We Log

**All API calls:**
```json
{
  "timestamp": "2025-12-21T10:30:00Z",
  "tenant_id": 1,
  "event_type": "run_created",
  "metadata": {
    "run_id": 42,
    "ticket_id": "123"
  }
}
```

**OAuth events:**
- Token issued
- Token refreshed
- Token revoked

**Export events:**
- Jira issue created
- Slack notification sent
- Export approved

**Configuration changes:**
- Jira config updated
- Slack config updated

### Log Retention

- **Standard logs:** 90 days
- **Audit logs:** 1 year
- **Security logs:** 2 years

### Log Access

**Admins can:**
- View audit logs via API
- Export logs (JSON/CSV)
- Filter by date, event type

**Query example:**
```bash
curl https://api.escalatesafe.com/v1/audit/logs?tenant_id=1&start=2025-12-01&end=2025-12-21
```

---

## Vulnerability Reporting

### Responsible Disclosure

**Found a security issue?**

**DO:**
1. Email: [security@frozo.ai](mailto:security@frozo.ai)
2. Include detailed description
3. Steps to reproduce
4. Wait for response (24-48 hours)

**DON'T:**
- Publicly disclose before fix
- Test on production without permission
- Access other users' data

### Scope

**In Scope:**
- Authentication bypass
- Data exposure
- SQL injection
- XSS vulnerabilities
- CSRF attacks
- OAuth vulnerabilities

**Out of Scope:**
- Social engineering
- DoS attacks
- Third-party services (Zendesk, Jira)
- Physical security

### Reward

While we don't currently offer a bug bounty program, we:
- Acknowledge reporters publicly (if desired)
- Provide detailed response
- Fast-track fixes for critical issues

---

## Security Checklist

### For Administrators

**Initial Setup:**
- [ ] Use strong encryption key
- [ ] Enable HTTPS only
- [ ] Configure OAuth properly
- [ ] Rotate API tokens quarterly

**Ongoing:**
- [ ] Review audit logs monthly
- [ ] Update dependencies regularly
- [ ] Monitor for unusual activity
- [ ] Train users on privacy policies

### For Developers

**Code Security:**
- [ ] Never commit secrets
- [ ] Use environment variables
- [ ] Validate all inputs
- [ ] Sanitize SQL queries
- [ ] Use prepared statements

**Deployment:**
- [ ] HTTPS enforced
- [ ] Database encrypted
- [ ] Secrets in vault
- [ ] Monitoring enabled

---

## Compliance Certifications

**Current:**
- ✅ GDPR compliant
- ✅ OAuth 2.0 standard
- ✅ HTTPS/TLS 1.2+

**Planned:**
- ⏳ SOC 2 Type II (2026)
- ⏳ ISO 27001 (2026)
- ⏳ HIPAA (enterprise tier)

---

## Contact

**Security Concerns:** [security@frozo.ai](mailto:security@frozo.ai)

**Privacy Questions:** [privacy@frozo.ai](mailto:privacy@frozo.ai)

**General Support:** [hello@frozo.ai](mailto:hello@frozo.ai)

---

**Last Updated:** December 21, 2025
