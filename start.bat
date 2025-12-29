@echo off
title ARGUS Fraud Detection System
color 0B

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║     _    ____   ____ _   _ ____                           ║
echo  ║    / \  |  _ \ / ___| | | / ___|                          ║
echo  ║   / _ \ | |_) | |  _| | | \___ \                          ║
echo  ║  / ___ \|  _ ^<| |_| | |_| |___) |                         ║
echo  ║ /_/   \_\_| \_\\____|\___/|____/                          ║
echo  ║                                                           ║
echo  ║           AI Fraud Detection System v3.2.0-india          ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

:: Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Check Node
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

echo [INFO] Starting ARGUS...
echo.

:: Start Backend
echo [1/2] Starting Backend on port 8000...
cd /d "%~dp0backend"
start "ARGUS Backend" cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8000"

:: Wait for backend
timeout /t 3 /nobreak >nul

:: Start Frontend
echo [2/2] Starting Frontend on port 3000...
cd /d "%~dp0frontend"
if not exist node_modules (
    echo [INFO] Installing npm packages...
    call npm install
)
start "ARGUS Frontend" cmd /c "npm run dev"

:: Wait and open browser
timeout /t 5 /nobreak >nul
echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║                    ARGUS is running!                      ║
echo ║                                                           ║
echo ║   Dashboard:  http://localhost:3000                       ║
echo ║   API:        http://localhost:8000                       ║
echo ║                                                           ║
echo ║   Press any key to open dashboard...                      ║
echo ╚═══════════════════════════════════════════════════════════╝
pause >nul

start http://localhost:3000
