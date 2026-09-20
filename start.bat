@echo off
chcp 65001 > nul
title EMP v7.0 - Integrated Management System
echo.
echo  +==================================+
echo  |   EMP v7.0 - Management System   |
echo  |   Ultimate Solutions - Altmt      |
echo  +==================================+
echo.

set PYTHON=py
where py >nul 2>&1 || set PYTHON=python

cd /d "%~dp0"
set EMP_DB_HOST=localhost
set EMP_DB_PORT=3306
set EMP_DB_USER=root
set EMP_DB_PASSWORD=
set EMP_DB_NAME=emp_system
%PYTHON% -c "import flask,flask_cors,mysql.connector" 2>nul || (
    echo Installing required libraries...
    %PYTHON% -m pip install flask flask-cors mysql-connector-python --quiet
)

echo  Starting server on: http://localhost:5000
echo  Press Ctrl+C to stop
echo.
start "" http://localhost:5000
%PYTHON% app\backend\app.py
pause
