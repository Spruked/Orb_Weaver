#!/bin/bash
set -e

echo "Setting up Orb Weaver - Website ORB Intelligence Engine..."

# Check dependencies
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed. Aborting." >&2; exit 1; }

# Backend setup
echo "📦 Setting up backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cd ..

# Frontend setup
echo "📦 Setting up frontend..."
cd frontend
npm install

cd ..

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Created .env from example. Please update with your credentials."
fi

echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  1. Backend: cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo "  2. Frontend: cd frontend && npm start"
echo ""
echo "Or use Docker: docker-compose up"
