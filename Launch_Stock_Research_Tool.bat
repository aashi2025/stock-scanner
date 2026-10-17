@echo off
title Indian Stock Research Platform - Zero Budget Dashboard
color 0a

echo ======================================================================
echo           INDIAN STOCK RESEARCH PLATFORM (ZERO BUDGET MVP)
echo ======================================================================
echo.
echo [1/3] Python environment check...
python --version
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in system PATH!
    pause
    exit /b
)

echo.
echo [2/3] Checking dependencies...
python -m pip install -r requirements.txt --quiet

echo.
echo [3/3] Starting Streamlit Mobile-Friendly Dashboard at http://localhost:8501 ...
start "" "http://localhost:8501"
python -m streamlit run streamlit_app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false

pause
