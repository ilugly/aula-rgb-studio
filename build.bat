@echo off
rem Builds dist\AULA-RGB-Studio.exe
cd /d "%~dp0"
if not exist .venv python -m venv .venv
.venv\Scripts\pip install -q -r requirements.txt pyinstaller || exit /b 1
.venv\Scripts\python tools\make_icon.py || exit /b 1
.venv\Scripts\pyinstaller --noconfirm --clean AULA-RGB-Studio.spec || exit /b 1
echo.
echo Done: dist\AULA-RGB-Studio.exe
