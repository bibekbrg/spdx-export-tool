@echo off
rem One-click live demo of the SPDX Export Tool (Windows).
cd /d "%~dp0"
title SPDX Export Tool - Live Demo

if not exist ".venv\Scripts\spdx-export.exe" (
  echo Setting up, first run only, please wait...
  python -m venv .venv || goto :nopython
  .venv\Scripts\python -m pip install --quiet -r requirements.txt
  .venv\Scripts\python -m pip install --quiet -e .
)
set TOOL=.venv\Scripts\spdx-export.exe
cls

echo ================================================================
echo   SPDX EXPORT TOOL - LIVE DEMO
echo   Converts scanner output - JSON or CSV - into a valid SPDX 2.3 file
echo ================================================================
echo.
echo DEMO 1 of 4 : a complete scan file. Expected: SPDX file is created.
echo ----------------------------------------------------------------
%TOOL% -i samples\valid_scan.json -o demo_output\valid_scan.spdx.json --creator "Bibek Roy"
echo   Exit code: %ERRORLEVEL%
echo.
pause

echo.
echo DEMO 2 of 4 : same data as CSV. Expected: works the same way.
echo ----------------------------------------------------------------
%TOOL% -i samples\valid_scan.csv -o demo_output\valid_scan_from_csv.spdx.json -q
echo   Exit code: %ERRORLEVEL%
echo.
pause

echo.
echo DEMO 3 of 4 : scan with missing fields. Expected: created, unknowns become NOASSERTION.
echo ----------------------------------------------------------------
%TOOL% -i samples\missing_fields_scan.json -o demo_output\missing_fields.spdx.json --gap-report demo_output\missing_fields_gap_report.txt
echo   Exit code: %ERRORLEVEL%
echo.
pause

echo.
echo DEMO 4 of 4 : broken scan. Expected: refused, every problem listed, nothing guessed.
echo ----------------------------------------------------------------
%TOOL% -i samples\broken_scan.json -o demo_output\broken.spdx.json
echo   Exit code: %ERRORLEVEL%
echo.
echo ================================================================
echo   Demo finished. Opening the generated SPDX file...
echo ================================================================
start "" notepad demo_output\valid_scan.spdx.json
pause
goto :eof

:nopython
echo Python was not found. Install Python 3.10 or newer from python.org and run this again.
pause
