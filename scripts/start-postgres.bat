@echo off
echo Starting PostgreSQL with Docker...
docker-compose up -d postgres
echo.
echo Waiting for PostgreSQL to be ready...
timeout /t 5 /nobreak > nul
docker-compose ps
echo.
echo PostgreSQL is running on localhost:5432
echo Database: exchange_data
echo Username: postgres
echo Password: postgres123
echo.
echo To stop PostgreSQL, run: stop-postgres.bat
pause