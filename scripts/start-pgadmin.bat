@echo off
echo Starting pgAdmin...
docker-compose up -d pgadmin
echo.
echo Waiting for pgAdmin to be ready...
timeout /t 10 /nobreak > nul
echo.
echo pgAdmin is running at: http://localhost:5050
echo Email: admin@exchange.local
echo Password: admin123
echo.
echo To connect to PostgreSQL in pgAdmin:
echo   Host: postgres (or host.docker.internal)
echo   Port: 5432
echo   Database: exchange_data
echo   Username: postgres
echo   Password: postgres123
echo.
start http://localhost:5050
pause