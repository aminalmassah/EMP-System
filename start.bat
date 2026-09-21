@echo off
chcp 65001 > nul
title EMP v7.0 - Integrated Management System
echo.
echo  +==================================+
echo  |   EMP v7.0 - Management System   |
echo  |   Ultimate Solutions - Altmt      |
echo  +==================================+
echo.

set PYTHON=python
where python >nul 2>&1 || set PYTHON=python3

cd /d "%~dp0"
%PYTHON% -c "import flask,flask_cors" 2>nul || (
    echo Installing required libraries...
    %PYTHON% -m pip install flask flask-cors --quiet
)

echo  Starting server on: http://localhost:5000
echo  Press Ctrl+C to stop
echo.
start "" http://localhost:5000
%PYTHON% app\backend\app.py
pause
