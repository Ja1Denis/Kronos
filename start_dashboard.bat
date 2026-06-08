@echo off
title Kronos Command Center
cd /d "E:\G\GeminiCLI\ai-test-project\kronos"

echo ==============================================
echo       KRONOS COMMAND CENTER (DASHBOARD)
echo ==============================================
echo.
echo Pokrecem Python Backend server...
echo Pripazite: Ako zatvorite ovaj prozor, server ce se ugasiti.
echo.

:: Otvaranje GUI stranice u zadanom web pregledniku. 
:: (start "" otvara URL asinkrono, tako da terminal nastavlja izvrsavanje na sljedecu liniju)
start "" "http://localhost:8000/dashboard/"

:: Zatim se na ovom prompt okruzenju podize fastAPI iz environmenta
:: Ukoliko vec neki "python server.py" radi na portu 8000 (ili ga IDE drzi zarobljenim), 
:: ugradeni "kill_port" u samome server.py razrijesiti ce zauzetost uticnice prije nego se uvicorn pokrene.
"E:\G\GeminiCLI\ai-test-project\.venv\Scripts\python.exe" src\server.py

pause
