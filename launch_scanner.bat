@echo off
title mmWave Deer Scan
cd /d "%~dp0"

echo ============================================================
echo  mmWave Deer Scanner
echo  Demo mode (simulated radar). Use --port COMx for hardware.
echo ============================================================
echo.

python scripts\live_scanner.py --demo
set EXITCODE=%ERRORLEVEL%
if %EXITCODE% NEQ 0 (
    echo.
    echo Scanner exited with error code %EXITCODE%.
    pause
)
