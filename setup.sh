#!/bin/bash

# EscalateSafe Setup Script
# This script sets up the development environment for EscalateSafe

set -e  # Exit on error

echo "🚀 EscalateSafe Setup"
echo "===================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi
echo "✅ Python 3 found: $(python3 --version)"

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi
echo "✅ Docker found: $(docker --version)"

if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi
echo "✅ Docker daemon is running"

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    echo "Please install Node.js from: https://nodejs.org/"
    exit 1
fi
echo "✅ Node.js found: $(node --version)"

echo ""
echo "📦 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

echo ""
echo "📥 Activating virtual environment and installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Python dependencies installed"

echo ""
echo "📥 Downloading spaCy model for PII detection..."
python -m spacy download en_core_web_lg
echo "✅ spaCy model downloaded"

echo ""
echo "🐳 Starting Docker infrastructure..."
docker-compose up -d
echo "✅ Docker containers started"

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check PostgreSQL
echo "Checking PostgreSQL..."
docker-compose exec -T postgres pg_isready -U postgres
echo "✅ PostgreSQL is ready"

# Check Redis
echo "Checking Redis..."
docker-compose exec -T redis redis-cli ping
echo "✅ Redis is ready"

echo ""
echo "🗄️  Creating database tables..."
python -c "
from api.db.database import engine
from api.db.models import Base
Base.metadata.create_all(bind=engine)
print('✅ Database tables created')
"

echo ""
echo "📱 Setting up Zendesk app..."
cd zendesk-app
if [ ! -d "node_modules" ]; then
    npm install
    echo "✅ Zendesk app dependencies installed"
else
    echo "✅ Zendesk app dependencies already installed"
fi
cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure your credentials:"
echo "   cp .env.example .env"
echo ""
echo "2. Edit .env and add your API keys:"
echo "   - OPENAI_API_KEY"
echo "   - ZENDESK credentials"
echo "   - JIRA credentials"
echo "   - SLACK_WEBHOOK_URL"
echo ""
echo "3. Start the backend server:"
echo "   source venv/bin/activate"
echo "   python api/main.py"
echo ""
echo "4. In a new terminal, start the Celery worker:"
echo "   source venv/bin/activate"
echo "   celery -A worker.celery_app worker --loglevel=info"
echo ""
echo "5. In another terminal, start the Zendesk app:"
echo "   cd zendesk-app"
echo "   npm run dev"
echo ""
echo "📚 See README.md for more details"
