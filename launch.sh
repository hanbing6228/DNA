#!/usr/bin/env bash
cd "$(dirname "$0")"
python -c "import flask" 2>/dev/null || python -m pip install flask
python -c "from database.db import init_db; init_db()" 2>/dev/null || true
echo ""
echo "========================================"
echo "🧬 DNA Genome Intelligence v2.1"
echo "Knowledge Graph + Reasoning + Drugs + Health"
echo "Open: http://localhost:5001"
echo "========================================"
python web_api_v2.py
