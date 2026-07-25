@echo off
setlocal
cd /d "%~dp0"

echo.
echo Score2Tab v0.2.2 hotfix 1
echo =============================
echo.

if not exist "score2tab\bass_verify.py" (
  echo Put this file inside the main Score2Tab folder,
  echo beside RUN_SCORE2TAB.bat.
  echo.
  echo Missing: %CD%\score2tab\bass_verify.py
  echo.
  pause
  exit /b 1
)

where powershell >nul 2>nul
if errorlevel 1 (
  echo PowerShell was not found.
  pause
  exit /b 1
)

echo Downloading the corrected measure lookup...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/lwp853/Test/score2tab-v0.2.2/score2tab-v0.2.2-patch/HOTFIX_V022_CONTEXT.py' -OutFile 'HOTFIX_V022_CONTEXT.py'"
if errorlevel 1 (
  echo.
  echo The hotfix could not be downloaded. Check your internet connection.
  echo.
  pause
  exit /b 1
)

set "PYTHON_LAUNCH=py -3"
where py >nul 2>nul
if errorlevel 1 set "PYTHON_LAUNCH=python"

echo Applying the hotfix...
%PYTHON_LAUNCH% HOTFIX_V022_CONTEXT.py
if errorlevel 1 (
  echo.
  echo The hotfix did not finish. Read the message above.
  echo.
  pause
  exit /b 1
)

echo.
echo Hotfix installed. Start Score2Tab with RUN_SCORE2TAB.bat.
echo.
pause
exit /b 0
