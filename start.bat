@echo off
:: ============================================
:: Exchange Dashboard - One-Click Startup
:: ============================================
:: Just double-click this file to start everything!

title Exchange Dashboard Launcher

echo.
echo ============================================
echo    EXCHANGE DASHBOARD - STARTING...
echo ============================================
echo.

:: Run the simplified Python startup script
python start.py

:: If Python script fails, show error and wait
if errorlevel 1 (
    echo.
    echo ============================================
    echo    ERROR: Startup failed!
    echo ============================================
    echo.
    echo Please check:
    echo 1. Python is installed
    echo 2. Docker Desktop is running
    echo 3. You're in the correct directory
    echo.
    echo For manual startup, see README.md
    echo.
    pause
)