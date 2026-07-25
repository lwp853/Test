@echo off
setlocal
cd /d "%~dp0"

echo.
echo Applying Score2Tab v0.2.2...
echo.

set "PYTHON_LAUNCH=py -3"
where py >nul 2>nul
if errorlevel 1 set "PYTHON_LAUNCH=python"

%PYTHON_LAUNCH% APPLY_V022_PATCH.py
if errorlevel 1 (
  echo.
  echo The patch did not finish. Read the message above.
  echo.
  pause
  exit /b 1
)

echo.
pause
exit /b 0
