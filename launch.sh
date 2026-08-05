#!/usr/bin/env bash
cd "$(dirname "$0")"
python -c "import flask" 2>/dev/null || python -m pip install flask
python -c "from database.db import init_db; init_db()" 2>/dev/null || true
echo ""
echo "========================================"
echo "DNA Genome Intelligence v3.0"
echo "Knowledge Graph + Reasoning + Longitudinal Memory"
echo "Health Timeline + Family Graph"
echo "Open: http://localhost:5001"
echo "========================================"
python web_api_v3.py
