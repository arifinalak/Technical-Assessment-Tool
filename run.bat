@echo off
cd /d "%~dp0"
echo === Panorama Sales Intelligence ===
if not exist venv (
  echo Creating virtual environment...
  python -m venv venv
)
call venv\Scripts\activate
echo Installing packages (first run only takes a few minutes)...
pip install -q -r requirements.txt
if not exist sales.db python prepare_data.py
if not exist chroma_db (
  echo Building the AI search index - needs internet the first time...
  python build_index.py
)
echo.
echo Starting the app at http://127.0.0.1:8000  (close this window to stop)
start "" http://127.0.0.1:8000
uvicorn app:app --host 127.0.0.1 --port 8000
