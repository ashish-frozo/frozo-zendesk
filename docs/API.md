# API Reference

Complete REST API reference for EscalateSafe backend.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Base URL](#base-url)
3. [Common Headers](#common-headers)
4. [Error Responses](#error-responses)
5. [Endpoints](#endpoints)
   - [Health](#health-endpoints)
   - [OAuth](#oauth-endpoints)
   - [Configuration](#configuration-endpoints)
   - [Runs](#runs-endpoints)

---

## Authentication

### OAuth 2.0

**For multi-tenant deployments:**
- Uses Zendesk OAuth 2.0
- Tokens stored per-tenant
- Auto-refresh on expiry

### API Token (Fallback)

**For development/testing:**
- Uses `X-Zendesk-Subdomain` header
- Falls back to environment variables
- Not recommended for production

---

## Base URL

```
Production:  https://your-app.up.railway.app
Development: http://localhost:8080
```

All endpoints are prefixed with `/v1/`

---

## Common Headers

### Required

```http
Content-Type: application/json
X-Zendesk-Subdomain: your-subdomain
```

### Optional

```http
Authorization: Bearer <oauth_token>
```

---

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Authentication failed |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

---

## Health Endpoints

### Get Health Status

Check if API is running.

**Request:**
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "escalatesafe-api",
  "version": "0.1.0"
}
```

**Status Codes:**
- `200` - Service healthy
- `503` - Service unhealthy

---

## OAuth Endpoints

### 1. Install App

Initiate OAuth flow for new tenant.

**Request:**
```http
POST /v1/oauth/install
Content-Type: application/json

{
  "subdomain": "customer",
  "locale": "en",
  "app_guid": "abc123"
}
```

**Response:**
```json
{
  "authorization_url": "https://customer.zendesk.com/oauth/authorizations/new?...",
  "tenant_id": 1,
  "subdomain": "customer"
}
```

**Status Codes:**
- `200` - Success
- `500` - Error creating tenant

---

### 2. OAuth Callback

Handle OAuth redirect from Zendesk.

**Request:**
```http
GET /v1/oauth/callback?code=AUTH_CODE&state=TENANT_ID
```

**Response:**
Redirects to:
```
https://{subdomain}.zendesk.com/agent/apps
```

**Status Codes:**
- `302` - Redirect to success page
- `400` - Invalid code or state

---

### 3. Get OAuth Status (Single Tenant)

Check OAuth configuration for a tenant.

**Request:**
```http
GET /v1/oauth/status/1
```

**Response:**
```json
{
  "tenant_id": 1,
  "subdomain": "customer",
  "status": "active",
  "has_access_token": true,
  "has_refresh_token": true,
  "token_expires_at": "2025-12-22T10:30:00",
  "scopes": "read write",
  "installed_at": "2025-12-21T08:00:00"
}
```

**Status Codes:**
- `200` - Success
- `404` - Tenant not found

---

### 4. Get All OAuth Status

Get OAuth status for all tenants (admin).

**Request:**
```http
GET /v1/oauth/status
```

**Response:**
```json
{
  "total_tenants": 2,
  "tenants": [
    {
      "tenant_id": 1,
      "subdomain": "customer1",
      "status": "active",
      "has_oauth": true,
      "token_expires_at": "2025-12-22T10:30:00"
    },
    {
      "tenant_id": 2,
      "subdomain": "customer2",
      "status": "pending",
      "has_oauth": false,
      "token_expires_at": null
    }
  ]
}
```

**Status Codes:**
- `200` - Success

---

## Configuration Endpoints

### 1. Get Jira Config

Retrieve Jira configuration for tenant.

**Request:**
```http
GET /v1/config/tenants/1/jira
X-Zendesk-Subdomain: customer
```

**Response:**
```json
{
  "server_url": "https://customer.atlassian.net",
  "email": "user@company.com",
  "api_token": "encrypted_token",
  "project_key": "SCRUM"
}
```

**Status Codes:**
- `200` - Success
- `404` - Config not found

---

### 2. Update Jira Config

Set Jira configuration for tenant.

**Request:**
```http
PUT /v1/config/tenants/1/jira
X-Zendesk-Subdomain: customer
Content-Type: application/json

{
  "server_url": "https://customer.atlassian.net",
  "email": "user@company.com",
  "api_token": "your_jira_token",
  "project_key": "SCRUM"
}
```

**Response:**
```json
{
  "message": "Jira configuration updated",
  "config_id": 5
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid input
- `404` - Tenant not found

---

### 3. Get Slack Config

Retrieve Slack configuration for tenant.

**Request:**
```http
GET /v1/config/tenants/1/slack
X-Zendesk-Subdomain: customer
```

**Response:**
```json
{
  "webhook_url": "https://hooks.slack.com/services/...",
  "channel": "#engineering-escalations"
}
```

**Status Codes:**
- `200` - Success
- `404` - Config not found

---

### 4. Update Slack Config

Set Slack configuration for tenant.

**Request:**
```http
PUT /v1/config/tenants/1/slack
X-Zendesk-Subdomain: customer
Content-Type: application/json

{
  "webhook_url": "https://hooks.slack.com/services/...",
  "channel": "#engineering-escalations"
}
```

**Response:**
```json
{
  "message": "Slack configuration updated",
  "config_id": 6
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid input

---

## Runs Endpoints

### 1. Create Run

Create new escalation run for a ticket.

**Request:**
```http
POST /v1/runs/
X-Zendesk-Subdomain: customer
Content-Type: application/json

{
  "ticket_id": "123",
  "include_internal_notes": false,
  "include_last_public_comments": 1
}
```

**Response:**
```json
{
  "run_id": 42,
  "status": "processing",
  "message": "Run created successfully"
}
```

**Processing Steps:**
1. Fetch ticket from Zendesk
2. Detect PII using Presidio
3. Redact sensitive information
4. Generate preview
5. Update status to `ready_for_review`

**Status Codes:**
- `201` - Created
- `400` - Invalid request
- `401` - OAuth not configured
- `404` - Ticket not found
- `500` - Processing failed

---

### 2. Get Run Status

Check run processing status.

**Request:**
```http
GET /v1/runs/42
X-Zendesk-Subdomain: customer
```

**Response (Processing):**
```json
{
  "id": 42,
  "ticket_id": "123",
  "status": "processing",
  "created_at": "2025-12-21T10:30:00",
  "updated_at": "2025-12-21T10:30:05",
  "redaction_report": null,
  "preview_available": false
}
```

**Response (Ready):**
```json
{
  "id": 42,
  "ticket_id": "123",
  "status": "ready_for_review",
  "created_at": "2025-12-21T10:30:00",
  "updated_at": "2025-12-21T10:30:10",
  "redaction_report": {
    "total_detections": 15,
    "entity_counts": {
      "EMAIL_ADDRESS": 3,
      "PHONE_NUMBER": 2,
      "PERSON": 4,
      "CREDIT_CARD": 1,
      "API_KEY": 5
    },
    "low_confidence_count": 0,
    "low_confidence_warnings": []
  },
  "preview_available": true
}
```

**Status Values:**
- `processing` - PII detection in progress
- `ready_for_review` - Preview ready
- `failed` - Processing error
- `exported` - Successfully exported to Jira

**Status Codes:**
- `200` - Success
- `404` - Run not found

---

### 3. Get Preview (Text)

Get redacted text preview.

**Request:**
```http
GET /v1/runs/42/preview/text
X-Zendesk-Subdomain: customer
```

**Response:**
```json
{
  "redacted_text": "Customer: [NAME_REDACTED]\nEmail: [EMAIL_REDACTED]\n...",
  "diff_segments": [],
  "redaction_summary": {
    "total_redactions": 15,
    "entities_redacted": {
      "EMAIL_ADDRESS": 3,
      "PHONE_NUMBER": 2
    },
    "original_length": 1500,
    "redacted_length": 1200
  }
}
```

**Status Codes:**
- `200` - Success
- `400` - Preview not available (wrong status)
- `404` - Run not found
- `500` - Redaction report missing

---

### 4. Approve & Export

Approve run and export to Jira + Slack.

**Request:**
```http
POST /v1/runs/42/approve
X-Zendesk-Subdomain: customer
Content-Type: application/json

{
  "jira": {
    "summary": "Customer login issue - escalated from ticket #123",
    "description": "See redacted content below...",
    "issue_type": "Bug",
    "priority": "High"
  },
  "slack": {
    "message": "New escalation from ticket #123"
  }
}
```

**Response:**
```json
{
  "run_id": 42,
  "status": "exported",
  "message": "Successfully exported to Jira: SCRUM-456",
  "jira_issue_key": "SCRUM-456",
  "jira_issue_url": "https://customer.atlassian.net/browse/SCRUM-456"
}
```

**Process:**
1. Validate run status = `ready_for_review`
2. Check for duplicate exports (idempotency)
3. Create Jira issue with redacted content
4. Post Slack notification (if configured)
5. Update run status to `exported`
6. Create audit log entry

**Idempotency:**
If run already exported, returns existing Jira issue:
```json
{
  "run_id": 42,
  "status": "already_exported",
  "message": "Already exported to SCRUM-456",
  "jira_issue_key": "SCRUM-456",
  "jira_issue_url": "https://customer.atlassian.net/browse/SCRUM-456"
}
```

**Status Codes:**
- `200` - Success (or already exported)
- `400` - Run not ready for review
- `404` - Run not found
- `500` - Export failed

---

## Rate Limiting

Currently no rate limiting enforced. Consider adding for production:
- 100 requests/minute per tenant
- 10 runs/minute per tenant

---

## Webhooks (Future)

Planned webhook support for:
- Run status updates
- Export completion
- OAuth token expiry warnings

---

## SDK Examples

### Python

```python
import requests

BASE_URL = "https://your-app.up.railway.app"
SUBDOMAIN = "customer"

headers = {
    "Content-Type": "application/json",
    "X-Zendesk-Subdomain": SUBDOMAIN
}

# Create run
response = requests.post(
    f"{BASE_URL}/v1/runs/",
    headers=headers,
    json={"ticket_id": "123"}
)
run = response.json()

# Poll for status
while True:
    response = requests.get(
        f"{BASE_URL}/v1/runs/{run['run_id']}",
        headers=headers
    )
    status = response.json()
    
    if status['status'] == 'ready_for_review':
        break
    
    time.sleep(1)

# Get preview
preview = requests.get(
    f"{BASE_URL}/v1/runs/{run['run_id']}/preview/text",
    headers=headers
).json()

# Approve
result = requests.post(
    f"{BASE_URL}/v1/runs/{run['run_id']}/approve",
    headers=headers,
    json={
        "jira": {
            "summary": "Escalation from ticket #123",
            "issue_type": "Bug"
        }
    }
).json()

print(f"Created Jira issue: {result['jira_issue_url']}")
```

### JavaScript

```javascript
const BASE_URL = "https://your-app.up.railway.app";
const SUBDOMAIN = "customer";

const headers = {
    "Content-Type": "application/json",
    "X-Zendesk-Subdomain": SUBDOMAIN
};

// Create run
const createRun = await fetch(`${BASE_URL}/v1/runs/`, {
    method: "POST",
    headers,
    body: JSON.stringify({ ticket_id: "123" })
});
const run = await createRun.json();

// Poll for status
let status;
while (true) {
    const response = await fetch(
        `${BASE_URL}/v1/runs/${run.run_id}`,
        { headers }
    );
    status = await response.json();
    
    if (status.status === "ready_for_review") break;
    await new Promise(r => setTimeout(r, 1000));
}

// Get preview
const preview = await fetch(
    `${BASE_URL}/v1/runs/${run.run_id}/preview/text`,
    { headers }
).then(r => r.json());

// Approve
const result = await fetch(
    `${BASE_URL}/v1/runs/${run.run_id}/approve`,
    {
        method: "POST",
        headers,
        body: JSON.stringify({
            jira: {
                summary: "Escalation from ticket #123",
                issue_type: "Bug"
            }
        })
    }
).then(r => r.json());

console.log(`Created: ${result.jira_issue_url}`);
```

---

## Support

**Questions?** Contact [hello@frozo.ai](mailto:hello@frozo.ai)

**Bugs?** Open issue: [GitHub Issues](https://github.com/ashish-frozo/frozo-zendesk/issues)
