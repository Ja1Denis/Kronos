@echo off
title Kronos AI Chat
mode con: cols=120 lines=40
cd /d "e:\G\GeminiCLI\ai-test-project\kronos"

:: Provjera venv-a
if not exist venv (
    echo [ERROR] Virtualno okruzenje nije pronadjeno. Pokreni setup.ps1 prvo.
    pause
    exit /b
)

echo [LAUNCH] Pokrecem Kronos Interaktivni Terminal...
call venv\Scripts\activate
python -m src.cli chat

echo.
echo [INFO] Kronos sesija zavrsena.
pause
