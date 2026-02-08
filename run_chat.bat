@echo off
title Kronos AI Chat
:: Postavi širinu i osiguraj veliki buffer za scrollanje (5000 linija)
mode con: cols=130
powershell -command "&{$H=get-host;$W=$H.ui.rawui;$B=$W.buffersize;$B.height=5000;$W.buffersize=$B;}"
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
