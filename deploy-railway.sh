#!/bin/bash

# Railway Deployment Script
# Run this script to prepare for Railway deployment

set -e  # Exit on error

echo "=========================================="
echo "EscalateSafe - Railway Deployment Setup"
echo "=========================================="
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "❌ Git repository not initialized"
    echo "Run: git init && git add . && git commit -m 'Initial commit'"
    exit 1
fi

echo "✓ Git repository detected"

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "⚠️  Railway CLI not installed"
    echo "Install with: npm install -g @railway/cli"
    echo "Or skip CLI and use web UI: https://railway.app"
    read -p "Continue without CLI? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ Railway CLI installed"
fi

# Check required files
echo ""
echo "Checking deployment files..."

files=(
    "Procfile"
    "railway.toml"
    "Aptfile"
    "runtime.txt"
    "requirements.txt"
    ".env.example"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ❌ $file missing"
        exit 1
    fi
done

echo ""
echo "=========================================="
echo "Railway Deployment Checklist"
echo "=========================================="
echo ""
echo "Before deploying, ensure you have:"
echo ""
echo "1. Cloudflare R2 or AWS S3 bucket created"
echo "   → Bucket name: escalatesafe-sanitized"
echo "   → Access keys generated"
echo ""
echo "2. External API credentials ready:"
echo "   → Zendesk Client ID & Secret"
echo "   → Jira Cloud ID & API Token"
echo "   → Slack Webhook URL"
echo "   → OpenAI API Key"
echo ""
echo "3. GitHub repository created and pushed:"
echo "   → git remote add origin <your-repo-url>"
echo "   → git push -u origin main"
echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "Option A: Deploy via Railway Web UI"
echo "  1. Visit: https://railway.app"
echo "  2. Create new project"
echo "  3. Add PostgreSQL plugin"
echo "  4. Add Redis plugin"
echo "  5. Deploy from GitHub repo"
echo "  6. Add environment variables"
echo ""
echo "Option B: Deploy via Railway CLI"
echo "  1. railway login"
echo "  2. railway init"
echo "  3. railway up"
echo "  4. railway add --database postgresql"
echo "  5. railway add --database redis"
echo "  6. railway variables set (copy from .env.example)"
echo ""
echo "=========================================="
echo ""

# Offer to create .env template for Railway
read -p "Create .env.railway template? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cat > .env.railway << 'EOF'
# Railway Environment Variables Template
# Copy these to Railway dashboard: Settings → Variables

# Database (auto-provided by Railway)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}

# Cloudflare R2 Storage (REQUIRED - create R2 bucket first)
S3_ENDPOINT=https://<YOUR-ACCOUNT-ID>.r2.cloudflarestorage.com
S3_ACCESS_KEY=<YOUR-R2-ACCESS-KEY>
S3_SECRET_KEY=<YOUR-R2-SECRET-KEY>
S3_BUCKET=escalatesafe-sanitized
S3_REGION=auto
S3_USE_SSL=true

# Zendesk OAuth (REQUIRED)
ZENDESK_CLIENT_ID=<YOUR-ZENDESK-CLIENT-ID>
ZENDESK_CLIENT_SECRET=<YOUR-ZENDESK-CLIENT-SECRET>
ZENDESK_REDIRECT_URI=https://<YOUR-RAILWAY-DOMAIN>/oauth/zendesk/callback

# Jira Cloud (REQUIRED)
JIRA_CLOUD_ID=<YOUR-JIRA-CLOUD-ID>
JIRA_API_TOKEN=<YOUR-JIRA-API-TOKEN>
JIRA_USER_EMAIL=<YOUR-JIRA-EMAIL>

# Slack (REQUIRED)
SLACK_WEBHOOK_URL=<YOUR-SLACK-WEBHOOK-URL>

# OpenAI (REQUIRED)
OPENAI_API_KEY=<YOUR-OPENAI-API-KEY>
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=1500

# Google Cloud Vision (OPTIONAL - for OCR fallback)
# GOOGLE_APPLICATION_CREDENTIALS=/app/gcloud-key.json

# Application Settings
APP_SECRET_KEY=$(openssl rand -hex 32)
CORS_ORIGINS=https://*.zendesk.com
LOG_LEVEL=INFO

# Tenant Defaults
DEFAULT_INTERNAL_NOTES_ENABLED=false
DEFAULT_LAST_PUBLIC_COMMENTS=1
DEFAULT_PDF_MAX_PAGES=10
DEFAULT_PDF_MAX_SIZE_MB=10
EOF
    echo "✓ Created .env.railway template"
    echo "  Edit this file with your credentials, then copy to Railway"
fi

echo ""
echo "=========================================="
echo "✅ Ready for Railway Deployment!"
echo "=========================================="
echo ""
echo "Documentation: railway_deployment_plan.md"
echo ""
