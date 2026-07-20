@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m bot.main
) else (
    python -m bot.main
)
