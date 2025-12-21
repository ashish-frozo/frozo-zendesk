#!/bin/bash

# Simplified Zendesk App Package Script
# Manually packages the app without Zendesk scaffold

set -e

echo "=========================================="
echo "EscalateSafe - Zendesk App Packaging"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# Check manifest exists
if [ ! -f "manifest.json" ]; then
    echo "❌ Error: manifest.json not found"
    exit 1
fi

echo "✓ Found manifest.json"
echo "✓ API URL: https://web-production-ccebe.up.railway.app"
echo ""

# Create clean package directory
echo "📦 Preparing package..."
rm -rf package
mkdir -p package

# Define package directory variable
PACKAGE_DIR="package"

# Copy required files
echo "  → Copying manifest.json"
cp manifest.json "$PACKAGE_DIR/"

echo "  → Copying assets (excluding src/)"
mkdir -p "$PACKAGE_DIR/assets"
# Copy only necessary HTML and image files
cp assets/*.html "$PACKAGE_DIR/assets/" 2>/dev/null || true
cp assets/*.png "$PACKAGE_DIR/assets/" 2>/dev/null || true
cp assets/*.svg "$PACKAGE_DIR/assets/" 2>/dev/null || true

# DO NOT copy src/ directory - .tsx files not valid for Zendesk packages

echo "  → Copying dist (if exists)"
if [ -d "dist" ]; then
    cp -r dist/* "$PACKAGE_DIR/assets/" 2>/dev/null || true
fi

echo "  → Copying translations"
mkdir -p "$PACKAGE_DIR/translations"
cp -r translations/* "$PACKAGE_DIR/translations/" 2>/dev/null || true

echo "  → Copying screenshots"
if [ -d "screenshots" ]; then
    mkdir -p "$PACKAGE_DIR/screenshots"
    cp screenshots/*.png "$PACKAGE_DIR/screenshots/" 2>/dev/null || true
fi

# Create ZIP
echo ""
echo "🗜️  Creating ZIP package..."
cd package
ZIP_NAME="escalatesafe-$(date +%Y%m%d-%H%M%S).zip"
zip -r "../$ZIP_NAME" . -x "*.DS_Store"
cd ..

# Clean up
rm -rf package

echo ""
echo "=========================================="
echo "✅ Package Created Successfully!"
echo "=========================================="
echo ""
echo "📦 File: $ZIP_NAME"
echo "📍 Location: $(pwd)/$ZIP_NAME"
echo "📏 Size: $(du -h "$ZIP_NAME" | cut -f1)"
echo ""
echo "=========================================="
echo "Upload to Zendesk:"
echo "=========================================="
echo ""
echo "1. Go to: https://YOUR-SUBDOMAIN.zendesk.com/admin/apps-integrations/apps/support-apps"
echo ""
echo "2. Click 'Upload privateapp'"
echo ""
echo "3. Select: $ZIP_NAME"
echo ""
echo "4. Click 'Install'"
echo ""
echo "5. Enable in ticket sidebar"
echo ""
echo "✅ Ready to test!"
echo ""
