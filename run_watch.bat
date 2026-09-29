@echo off
rem Tarheel Vendor Watch launcher
rem   Double-click:        runs with progress on screen, waits for a key at the end
rem   Task Scheduler:      add the argument /auto  (no pause; output goes to vendor_watch.log)
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set "PY=python"
where py >nul 2>nul && set "PY=py"
if /i "%~1"=="/auto" (
  %PY% vendor_watch.py >> vendor_watch.log 2>&1
  exit /b
)
%PY% vendor_watch.py
echo.
pause
