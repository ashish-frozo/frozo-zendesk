#!/bin/bash

# Zendesk App Build & Package Script
# Automates the build and packaging process for EscalateSafe Zendesk app

set -e  # Exit on error

echo "=========================================="
echo "EscalateSafe - Zendesk App Deployment"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "manifest.json" ]; then
    echo "❌ Error: manifest.json not found"
    echo "Please run this script from the zendesk-app directory"
    exit 1
fi

echo "✓ Found manifest.json"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not installed"
    echo "Install from: https://nodejs.org"
    exit 1
fi

echo "✓ Node.js installed: $(node --version)"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm not installed"
    exit 1
fi

echo "✓ npm installed: $(npm --version)"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
npm install

# Build the app
echo ""
echo "🔨 Building Zendesk app..."
npm run build

# Check if zcli is installed
if ! command -v zcli &> /dev/null; then
    echo ""
    echo "⚠️  Zendesk CLI (zcli) not found"
    echo "Installing @zendesk/zcli globally..."
    npm install -g @zendesk/zcli
fi

echo "✓ Zendesk CLI installed: $(zcli --version)"

# Package the app
echo ""
echo "📦 Packaging app..."
zcli apps:package

# Find the generated zip file
ZIP_FILE=$(ls -t *.zip 2>/dev/null | head -n 1)

if [ -z "$ZIP_FILE" ]; then
    echo "❌ No .zip file found"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Zendesk App Packaged Successfully!"
echo "=========================================="
echo ""
echo "📦 Package: $ZIP_FILE"
echo "📍 Location: $(pwd)/$ZIP_FILE"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Go to your Zendesk Admin Center:"
echo "   https://YOUR-SUBDOMAIN.zendesk.com/admin/apps-integrations/apps/support-apps"
echo ""
echo "2. Click 'Upload private app'"
echo ""
echo "3. Upload this file:"
echo "   $ZIP_FILE"
echo ""
echo "4. Configure the app:"
echo "   - API Base URL is already set to:"
echo "   https://web-production-ccebe.up.railway.app"
echo ""
echo "5. Click 'Install' and enable in ticket sidebar"
echo ""
echo "=========================================="
echo ""
echo "🧪 Test with a sample ticket containing PII:"
echo "   - Email: john.doe@example.com"
echo "   - Phone: +1-555-123-4567"
echo "   - API Key: Bearer abc123xyz"
echo ""
echo "The app should redact all PII automatically!"
echo ""
