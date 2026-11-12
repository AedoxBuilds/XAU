@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Environment missing. Run setup_windows.bat first.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
echo Stage 1: preprocessing historical MT5 data...
python stage1_preprocess.py
if errorlevel 1 goto failed
echo Stage 2: training and chronological test...
python stage2_train.py
if errorlevel 1 goto failed
echo Training pipeline finished. Review models/model_metrics.csv and models/quant_stats.csv.
pause
exit /b 0
:failed
echo Pipeline failed. Review the error above.
pause
exit /b 1
