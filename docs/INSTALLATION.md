# Installation Guide

Complete step-by-step installation guide for EscalateSafe.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Backend Deployment](#backend-deployment)
3. [Database Setup](#database-setup)
4. [OAuth Configuration](#oauth-configuration)
5. [Zendesk App Installation](#zendesk-app-installation)
6. [Jira Configuration](#jira-configuration)
7. [Slack Configuration](#slack-configuration-optional)
8. [Verification](#verification)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts

- ✅ **Zendesk** - Suite or Support Professional plan
- ✅ **Jira Cloud** - Any plan with API access
- ✅ **Railway/Heroku** - For backend hosting
- ⚠️ **Slack** - Optional, for notifications

### Required Access

- Admin access to Zendesk account
- Jira admin or project admin
- Ability to create OAuth apps in Zendesk
- Database (PostgreSQL 14+)

---

## Backend Deployment

### Option 1: Railway (Recommended)

**1. Fork the repository**
```bash
git clone https://github.com/your-org/frozo-zendesk
cd frozo-zendesk
```

**2. Create Railway project**
- Go to [railway.app](https://railway.app)
- Click "New Project" → "Deploy from GitHub repo"
- Select your forked repository
- Choose "Deploy Now"

**3. Add PostgreSQL database**
- In Railway dashboard, click "New" → "Database" → "PostgreSQL"
- Database URL will be auto-added to environment

**4. Set environment variables**

Go to project → Variables, add:

```bash
# Database (auto-added by Railway)
DATABASE_URL=postgresql://...

# Encryption
ENCRYPTION_KEY=<generate-32-byte-key>  # Generate with: openssl rand -hex 32

# Zendesk OAuth (get from Zendesk admin)
ZENDESK_CLIENT_ID=your_client_id
ZENDESK_CLIENT_SECRET=your_client_secret

# Backend URL (from Railway deployment)
API_BASE_URL=https://your-app.up.railway.app

# Zendesk API (temporary, for testing only)
ZENDESK_EMAIL=your.email@company.com
ZENDESK_API_TOKEN=your_api_token
ZENDESK_SUBDOMAIN=yourcompany

# Jira (from Jira Cloud)
JIRA_CLOUD_ID=yourcompany
JIRA_USER_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_jira_token

# Slack (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

**5. Deploy**
- Railway auto-deploys on git push
- Wait for deployment to complete (~2-3 minutes)
- Note your deployment URL: `https://your-app.up.railway.app`

### Option 2: Heroku

```bash
# Install Heroku CLI
brew install heroku/brew/heroku

# Login
heroku login

# Create app
heroku create your-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Set environment variables
heroku config:set ENCRYPTION_KEY=$(openssl rand -hex 32)
heroku config:set ZENDESK_CLIENT_ID=your_client_id
# ... (set all variables from above)

# Deploy
git push heroku main

# Run migrations
heroku run python -c "from api.db.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

### Option 3: Docker

```bash
# Build image
docker build -t escalatesafe-api .

# Run with environment file
docker run -d \
  --env-file .env \
  -p 8080:8080 \
  escalatesafe-api
```

---

## Database Setup

### Run Migrations

**If using Railway:**
Railway runs migrations automatically on deployment via `railway-postbuild.sh`.

**If manual setup needed:**

```bash
# Connect to your database
psql $DATABASE_URL

# Run migration scripts
\i api/db/migrations/001_initial_schema.sql
\i api/db/migrations/002_add_audit_log.sql
\i api/db/migrations/003_add_oauth_to_tenants.sql
```

**Verify tables:**
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
```

Should show:
- tenants
- users
- tenant_configs
- runs
- exports
- audit_events

---

## OAuth Configuration

### 1. Register OAuth App in Zendesk

**Steps:**
1. Go to Zendesk Admin → **Apps and integrations** → **APIs** → **Zendesk API**
2. Click **OAuth Clients** tab
3. Click **Add OAuth Client**
4. Fill in:
   - **Client Name:** EscalateSafe
   - **Description:** PII-safe ticket escalation
   - **Company:** Your Company Name
   - **Logo:** Upload escalatesafe logo
   - **Unique Identifier:** `escalatesafe_oauth_client`
   - **Redirect URLs:** `https://your-backend.up.railway.app/v1/oauth/callback`
5. Click **Save**
6. **Copy Client ID and Secret** - save these securely!

### 2. Add OAuth Credentials to Backend

Update Railway environment variables:
```bash
ZENDESK_CLIENT_ID=escalatesafe_oauth_client
ZENDESK_CLIENT_SECRET=your_secret_here
```

### 3. Test OAuth Endpoint

```bash
curl https://your-backend.up.railway.app/v1/oauth/status

# Should return:
#{
#  "total_tenants": 0,
#  "tenants": []
#}
```

---

## Zendesk App Installation

### 1. Package the App

```bash
cd zendesk-app
./package-app.sh

# Creates: escalatesafe-YYYYMMDD-HHMMSS.zip
```

### 2. Upload to Zendesk

**Steps:**
1. Go to Zendesk Admin → **Apps and integrations** → **Apps** → **Support Apps**
2. Click **Upload private app**
3. Select the ZIP file created above
4. Click **Upload**

**Configuration:**
- **API Base URL:** `https://your-backend.up.railway.app`

### 3. Install the App

1. After upload, click **Install**
2. Choose where to display:
   - ✅ **Ticket sidebar** (required)
   - ✅ **Top bar** (for installation flow)
3. Click **Install**

### 4. Enable in Ticket View

1. Go to any ticket
2. Look for EscalateSafe in right sidebar
3. If not visible, click "Apps" and enable it

---

## Jira Configuration

### 1. Generate Jira API Token

1. Go to [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Name it: "EscalateSafe Integration"
4. **Copy the token** - save it securely!

### 2. Add to Backend

Update Railway environment:
```bash
JIRA_CLOUD_ID=yourcompany  # From yourcompany.atlassian.net
JIRA_USER_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_jira_api_token_here
```

### 3. Configure in App

1. Open EscalateSafe in a ticket
2. Click **⚙️ Settings**
3. Fill in Jira section:
   - **Server URL:** `https://yourcompany.atlassian.net`
   - **Email:** Your Jira email
   - **API Token:** Paste the token from step 1
   - **Project Key:** e.g., `SCRUM`, `ENG`, `SUP`
4. Click **💾 Save Jira**
5. Look for  **"✓ Jira configuration saved!"** message

### 4. Test Connection

Jira credentials are tested when creating first escalation.

---

## Slack Configuration (Optional)

### 1. Create Incoming Webhook

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Name: "EscalateSafe"
4. Choose your workspace
5. Go to **Incoming Webhooks**
6. Toggle **Activate Incoming Webhooks** ON
7. Click **Add New Webhook to Workspace**
8. Choose a channel (e.g., #engineering-escalations)
9. Click **Allow**
10. **Copy the Webhook URL**

### 2. Add to Backend (Optional Global Default)

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX
```

### 3. Configure in App

1. Open EscalateSafe settings
2. Fill in Slack section:
   - **Webhook URL:** Paste from step 1
   - **Channel:** #engineering-escalations
3. Click **💾 Save Slack**

---

## Verification

### 1. Health Check

```bash
curl https://your-backend.up.railway.app/health

# Should return:
# {
#   "status": "healthy",
#   "service": "escalatesafe-api",
#   "version": "0.1.0"
# }
```

### 2. Test Full Flow

1. **Open a test ticket** in Zendesk
2. **Click EscalateSafe** in sidebar
3. **Configure settings** (if first time)
4. **Click "🚀 Generate Engineering Pack"**
5. **Review preview** - verify PII is redacted
6. **Click "✓ Approve & Create Jira Issue"**
7. **Check Jira** - issue should be created
8. **Check Slack** (if configured) - notification sent

### 3. Verify OAuth (Marketplace apps only)

For marketplace deployment:
1. Uninstall and reinstall app
2. Watch for OAuth authorization screen
3. Grant permissions
4. Verify tokens stored in database

---

## Troubleshooting

### Backend Issues

**Problem:** 502 Bad Gateway
```bash
# Check Railway logs
railway logs

# Look for Python errors
# Common causes:
# - Missing environment variables
# - Database connection failed
# - Migration not run
```

**Problem:** Database connection error
```bash
# Verify DATABASE_URL is set
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Run migrations
python -m api.db.migrations.run_all
```

### Zendesk App Issues

**Problem:** App not loading
- Check browser console for errors
- Verify API_BASE_URL is correct
- Check CORS is enabled on backend
- Verify app is enabled in ticket view

**Problem:** OAuth not configured error
- Ensure OAuth credentials set in Railway
- Check tenant has OAuth tokens (or fallback env vars set)
- Verify callback URL matches in Zendesk OAuth client

### Jira Issues

**Problem:** Jira issue creation fails
- Verify JIRA_API_TOKEN is valid
- Check project key exists
- Ensure user has permission to create issues
- Check network connectivity from backend to Jira

**Problem:** "400 Bad Request" from Jira
- Project key might be wrong
- Issue type might not exist in project
- Required fields might be missing

### Slack Issues

**Problem:** Slack notifications not sent
- Verify webhook URL is correct
- Check webhook hasn't been revoked
- Ensure channel still exists
- Check backend logs for Slack errors

---

## Next Steps

After installation:
1. ✅ Read [User Guide](USER_GUIDE.md) for usage instructions
2. ✅ See [Security Guide](SECURITY.md) for privacy info
3. ✅ Check [API Reference](API.md) for integration options

---

## Support

**Issues?** Open a ticket: [GitHub Issues](https://github.com/ashish-frozo/frozo-zendesk/issues)

**Email:** [hello@frozo.ai](mailto:hello@frozo.ai)

**Documentation:** [docs/](.)
