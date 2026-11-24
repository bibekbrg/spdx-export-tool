@echo off
rem One-click web preview of the SPDX Export Tool (Windows).
cd /d "%~dp0"
title SPDX Export Tool - Web Preview

if not exist ".venv\Scripts\python.exe" (
  echo Setting up, first run only, please wait...
  python -m venv .venv || goto :nopython
)
.venv\Scripts\python -c "import spdx_export.web" 2>nul || (
  echo Installing, please wait...
  .venv\Scripts\python -m pip install --quiet -r requirements.txt
  .venv\Scripts\python -m pip install --quiet -e .
)

echo Starting the web preview. Your browser will open automatically.
echo Keep this window open while you use the page. Close it to stop.
echo.
.venv\Scripts\python -m spdx_export.web
pause
goto :eof

:nopython
echo Python was not found. Install Python 3.10 or newer from python.org and run this again.
pause
