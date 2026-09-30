@echo off
setlocal
cd /d "%~dp0backend"

if exist ".venv\Scripts\python.exe" (
    echo Using .venv
    ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    goto :eof
)

if exist "venv\Scripts\python.exe" (
    echo Using venv
    "venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    goto :eof
)

echo No virtual environment found.
echo Create one first:
echo   python -m venv .venv
echo   .\.venv\Scripts\Activate.ps1
echo   python -m pip install -r requirements.txt
pause
