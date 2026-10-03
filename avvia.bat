@echo off
rem Avvia Minecraft Builder con il Python di Windows (launcher "py"),
rem installando le dipendenze al primo avvio se mancano.
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    echo Python per Windows non trovato. Installalo da https://www.python.org/downloads/
    pause
    exit /b 1
)
py -3 -c "import PyQt6, requests, bs4" >nul 2>nul
if errorlevel 1 (
    echo Installazione delle dipendenze...
    py -3 -m pip install -r requirements.txt
)
py -3 main.py %*
if errorlevel 1 pause
