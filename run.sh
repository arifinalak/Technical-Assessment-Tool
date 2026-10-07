#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt
[ -f sales.db ] || python prepare_data.py
[ -d chroma_db ] || python build_index.py || echo "Index build skipped (needs internet once)."
echo "Open http://127.0.0.1:8000"
uvicorn app:app --host 127.0.0.1 --port 8000
