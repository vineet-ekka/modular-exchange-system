@echo off
echo ============================================================
echo STARTING EXCHANGE DASHBOARD
echo ============================================================
echo.

REM Check if PostgreSQL is running
docker ps | findstr exchange_postgres >nul 2>&1
if errorlevel 1 (
    echo Starting PostgreSQL...
    docker-compose up -d
    timeout /t 5 /nobreak >nul
    echo PostgreSQL started
) else (
    echo PostgreSQL is already running
)

echo.
echo Starting API server...
start "API Server" cmd /k "python api.py"
timeout /t 3 /nobreak >nul

echo Starting React dashboard...
start "React Dashboard" cmd /k "cd dashboard && npm start"
timeout /t 3 /nobreak >nul

echo Starting data collector...
start "Data Collector" cmd /k "python main.py --loop --interval 30 --quiet"

echo.
echo ============================================================
echo DASHBOARD STARTUP COMPLETE
echo ============================================================
echo.
echo Services running:
echo   API Server: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Dashboard: http://localhost:3000
echo   PostgreSQL: localhost:5432
echo.
echo Opening dashboard in browser...
timeout /t 5 /nobreak >nul
start http://localhost:3000

echo.
echo Press any key to exit (services will continue running)...
pause >nul