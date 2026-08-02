#!/bin/bash
set -e

echo "ORB Dock Station — Installation"
echo "================================"

command -v python3 >/dev/null 2>&1 || { echo "Python 3 required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js required"; exit 1; }

echo "Installing backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

echo "Installing frontend..."
cd frontend
npm install
cd ..

echo "Installing desktop wrapper..."
cd desktop
npm install
cd ..

echo ""
echo "Installation complete."
echo ""
echo "To start development:"
echo "  Terminal 1: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "  Terminal 2: cd frontend && npm run dev"
echo ""
echo "Default login: owner@orb.system / orb-owner-2026"
