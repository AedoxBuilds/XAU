@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo Aedox Gold Analysis Agent - Setup
echo ==========================================
where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher not found. Install Python 3.11 64-bit first.
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 (
        echo Could not create Python 3.11 environment.
        echo Install Python 3.11 64-bit and retry.
        pause
        exit /b 1
    )
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto failed
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Setup complete. Edit config.py and set MT5_SYMBOL to your broker symbol.
pause
exit /b 0
:failed
echo Setup failed. Read the error above.
pause
exit /b 1
