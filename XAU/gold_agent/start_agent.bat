@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Environment missing. Run setup_windows.bat first.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
echo Starting Aedox Gold Analysis Agent in ANALYSIS-ONLY mode...
echo No MT5 orders will be placed, modified, or closed.
python run.py
pause
