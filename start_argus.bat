@echo off
echo =======================================================
echo          Project ARGUS - Startup Sequence
echo =======================================================

echo [1/2] Starting Backend Server (FastAPI + Websockets)...
start "ARGUS Backend" /D "%~dp0backend" cmd /k ".\venv\Scripts\python.exe main.py"

echo [2/2] Starting Frontend App (React + Vite)...
start "ARGUS Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

echo.
echo ARGUS startup initiated! 
echo Two terminal windows have opened for the backend and frontend.
echo.
pause
