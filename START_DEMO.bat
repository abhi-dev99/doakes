@echo off
REM ARGUS Fraud Detection System - Hackathon Demo Launcher
REM =======================================================

echo.
echo ========================================
echo   ARGUS Fraud Detection System
echo   Hackathon Demo - Starting Services
echo ========================================
echo.

REM Check if already running
echo [1/5] Checking for existing processes...
netstat -ano | findstr ":8000" >nul
if %errorlevel%==0 (
    echo    WARNING: Port 8000 already in use!
    echo    Killing existing backend process...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do taskkill /F /PID %%a >nul 2>&1
    timeout /t 2 >nul
)

netstat -ano | findstr ":3000" >nul
if %errorlevel%==0 (
    echo    WARNING: Port 3000 already in use!
    echo    Frontend may already be running
)

echo    ✓ Ports checked
echo.

REM Start Backend
echo [2/5] Starting Backend API Server...
cd backend
if not exist venv (
    echo    Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
echo    ✓ Virtual environment activated
echo    Installing dependencies...
pip install -q -r requirements.txt
echo    ✓ Dependencies ready
echo    Launching FastAPI server on http://localhost:8000

start "ARGUS Backend" cmd /k "python main.py"
timeout /t 5 >nul

echo    ✓ Backend started (PID: Running in new window)
echo.

REM Start Frontend
echo [3/5] Starting Frontend Dashboard...
cd ..\frontend

if not exist node_modules (
    echo    Installing Node.js dependencies...
    call npm install
)

echo    ✓ Dependencies ready
echo    Launching Vite dev server on http://localhost:3000

start "ARGUS Frontend" cmd /k "npm run dev"
timeout /t 5 >nul

echo    ✓ Frontend started (PID: Running in new window)
echo.

REM Wait for services
echo [4/5] Waiting for services to initialize...
timeout /t 8 >nul
echo    ✓ Services initialized
echo.

REM Open Browser
echo [5/5] Opening dashboard in browser...
start http://localhost:3000
echo    ✓ Browser launched
echo.

echo ========================================
echo   ✅ ARGUS is READY!
echo ========================================
echo.
echo   Backend API:  http://localhost:8000
echo   Frontend UI:  http://localhost:3000
echo   API Docs:     http://localhost:8000/docs
echo.
echo   📊 Click "Start Simulation" to see
echo      real-time fraud detection in action!
echo.
echo   🎯 DEMO FEATURES:
echo   • Pre-Authorization BLOCK/CHALLENGE/ALLOW
echo   • Graph-based Fraud Ring Detection
echo   • Deep Learning Sequence Analysis
echo   • Explainable AI (XAI)
echo   • Multi-Channel Alerts
echo   • Phishing Protection
echo   • Merchant Reputation
echo   • Case Management
echo.
echo   Press Ctrl+C in backend/frontend windows to stop
echo ========================================
echo.

pause
