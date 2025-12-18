# Railway Deployment - Step-by-Step Guide

This guide walks you through deploying EscalateSafe to Railway.

## Prerequisites ✅

- [ ] GitHub account and repository
- [ ] Railway account (https://railway.app)
- [ ] Cloudflare R2 or AWS S3 bucket
- [ ] API credentials: Zendesk, Jira, Slack, OpenAI

## Step 1: Prepare Git Repository

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - EscalateSafe"

# Create GitHub repository and push
git remote add origin https://github.com/YOUR-USERNAME/escalatesafe.git
git branch -M main
git push -u origin main
```

## Step 2: Create Railway Project

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Authorize GitHub and select your repository
5. Project name: `escalatesafe-production`

## Step 3: Add PostgreSQL Database

1. In Railway project → Click "New"
2. Select "Database" → "Add PostgreSQL"
3. Wait for provisioning (~30 seconds)
4. Note: `DATABASE_URL` is auto-injected into services

## Step 4: Add Redis Database

1. In Railway project → Click "New"
2. Select "Database" → "Add Redis"
3. Wait for provisioning (~30 seconds)
4. Note: `REDIS_URL` is auto-injected into services

## Step 5: Configure API Service

Your repository is already connected. Now configure:

### A. Service Settings

1. Click on the service (should be auto-created from repo)
2. Settings → Name: `escalatesafe-api`
3. Settings → Start Command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 2`

### B. Generate Public Domain

1. Settings → Networking
2. Click "Generate Domain"
3. Copy domain (e.g., `escalatesafe-api-production.up.railway.app`)

### C. Add Environment Variables

Settings → Variables → Raw Editor → Paste:

```bash
# Database (auto-provided)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}

# S3 Storage (FILL IN YOUR VALUES)
S3_ENDPOINT=https://YOUR-ACCOUNT-ID.r2.cloudflarestorage.com
S3_ACCESS_KEY=YOUR_R2_ACCESS_KEY
S3_SECRET_KEY=YOUR_R2_SECRET_KEY
S3_BUCKET=escalatesafe-sanitized
S3_REGION=auto
S3_USE_SSL=true

# Zendesk (FILL IN YOUR VALUES)
ZENDESK_CLIENT_ID=YOUR_ZENDESK_CLIENT_ID
ZENDESK_CLIENT_SECRET=YOUR_ZENDESK_CLIENT_SECRET
ZENDESK_REDIRECT_URI=https://YOUR-RAILWAY-DOMAIN/oauth/zendesk/callback

# Jira (FILL IN YOUR VALUES)
JIRA_CLOUD_ID=YOUR_JIRA_CLOUD_ID
JIRA_API_TOKEN=YOUR_JIRA_API_TOKEN
JIRA_USER_EMAIL=YOUR_EMAIL

# Slack (FILL IN YOUR VALUES)
SLACK_WEBHOOK_URL=YOUR_SLACK_WEBHOOK_URL

# OpenAI (FILL IN YOUR VALUES)
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=1500

# App Settings (GENERATE SECRET)
APP_SECRET_KEY=GENERATE_WITH_OPENSSL_RAND_HEX_32
CORS_ORIGINS=https://*.zendesk.com
LOG_LEVEL=INFO

# Defaults
DEFAULT_INTERNAL_NOTES_ENABLED=false
DEFAULT_LAST_PUBLIC_COMMENTS=1
DEFAULT_PDF_MAX_PAGES=10
DEFAULT_PDF_MAX_SIZE_MB=10
```

**Generate APP_SECRET_KEY:**
```bash
openssl rand -hex 32
```

### D. Deploy

Railway auto-deploys on push. Check "Deployments" tab for build logs.

## Step 6: Create Worker Service

1. In Railway project → Click "New"
2. Select "Empty Service"
3. Name: `escalatesafe-worker`

### A. Connect to Repository

1. Settings → Source → "Connect to Repo"
2. Select same GitHub repository
3. Start Command: `celery -A worker.celery_app worker --loglevel=info --concurrency=2`

### B. Increase Resources

1. Settings → Resources
2. Memory: 1024 MB (1GB)
3. vCPU: 1

### C. Remove Public Domain

1. Settings → Networking
2. Remove any public domains (worker doesn't need external access)

### D. Add Same Environment Variables

Copy all environment variables from API service.

### E. Deploy

Should auto-deploy. Check logs for "celery@worker ready."

## Step 7: Run Database Migrations

### Option A: Railway CLI

```bash
# Install CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Run migration
railway run -s escalatesafe-api python -c "from api.db.database import engine; from api.db.models import Base; Base.metadata.create_all(bind=engine)"
```

### Option B: One-Time Job

1. Create new service: "Migration Job"
2. Same repo, but start command:
   ```bash
   python -c "from api.db.database import engine; from api.db.models import Base; Base.metadata.create_all(bind=engine)"
   ```
3. Run once, then delete service

## Step 8: Setup Cloudflare R2

### Create Bucket

1. Cloudflare Dashboard → R2
2. "Create Bucket" → Name: `escalatesafe-sanitized`
3. Location: Automatic

### Generate API Tokens

1. R2 → Manage R2 API Tokens
2. "Create API Token"
3. Permissions: Object Read & Write
4. Copy Access Key ID and Secret Access Key

### Update Railway Variables

Update in both API and Worker services:
- `S3_ENDPOINT`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`

## Step 9: Verify Deployment

### Check Health Endpoint

```bash
curl https://YOUR-RAILWAY-DOMAIN.up.railway.app/health
```

Expected:
```json
{
  "status": "healthy",
  "service": "escalatesafe-api",
  "version": "0.1.0"
}
```

### Check Logs

**API Service:**
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Worker Service:**
```
[2025-12-18 12:00:00] celery@worker ready.
```

### Test Database Connection

```bash
railway run -s escalatesafe-api python -c "from api.db.database import SessionLocal; db = SessionLocal(); print('✓ DB connected'); db.close()"
```

## Step 10: Deploy Zendesk App

### Update Manifest

1. Edit `zendesk-app/manifest.json`:

```json
{
  "parameters": [
    {
      "name": "api_base_url",
      "type": "url",
      "default": "https://YOUR-RAILWAY-DOMAIN.up.railway.app"
    }
  ]
}
```

### Build and Package

```bash
cd zendesk-app
npm install
npm run build
npm install -g @zendesk/zcli
zcli apps:package
```

### Upload to Zendesk

1. Zendesk Admin → Apps and integrations → Zendesk Support apps
2. "Upload private app"
3. Upload generated `.zip` file
4. Install to your account

## Post-Deployment Checklist

- [ ] API health check returns 200
- [ ] Worker logs show "ready"
- [ ] Database tables created (verify 8 tables exist)
- [ ] Redis connection working
- [ ] S3 upload test successful
- [ ] Create test run via Zendesk app
- [ ] Verify PII detection
- [ ] Test Jira issue creation
- [ ] Test Slack notification
- [ ] Monitor Railway logs for errors

## Monitoring

### Railway Dashboard

- **Metrics:** CPU, Memory, Network (per service)
- **Logs:** Real-time, searchable
- **Alerts:** Configure webhooks

### Optional: Add Sentry for Error Tracking

Already in requirements.txt. Add to `api/main.py`:

```python
import sentry_sdk

sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    environment="production",
)
```

## Troubleshooting

### Build Fails

**Issue:** Missing Tesseract  
**Fix:** Ensure `Aptfile` exists in root directory

**Issue:** Python version mismatch  
**Fix:** Ensure `runtime.txt` has `python-3.11`

### Worker OOM (Out of Memory)

**Issue:** Worker crashes during PDF processing  
**Fix:** Increase worker RAM to 1.5GB or 2GB

### Database Connection Errors

**Issue:** `OperationalError: could not connect`  
**Fix:** Verify `DATABASE_URL=${{Postgres.DATABASE_URL}}` is set

### S3 Upload Fails

**Issue:** `S3UploadFailedError`  
**Fix:** Verify R2 credentials and endpoint URL

## Cost Monitoring

Check Railway dashboard under "Usage" tab.

Expected: ~$15-20/month after $5 free credit.

---

**Deployment Complete! 🎉**

Your EscalateSafe system is now live on Railway.
