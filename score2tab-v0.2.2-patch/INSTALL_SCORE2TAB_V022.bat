@echo off
setlocal
cd /d "%~dp0"

echo.
echo Score2Tab v0.2.2 installer
echo ============================
echo.

if not exist "score2tab\pipeline.py" (
  echo This installer must be placed inside the extracted Score2Tab-Windows-v0.2.1 folder.
  echo I could not find score2tab\pipeline.py here:
  echo %CD%
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

echo Downloading the v0.2.2 patch files...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/lwp853/Test/score2tab-v0.2.2/score2tab-v0.2.2-patch/APPLY_V022_PATCH.py' -OutFile 'APPLY_V022_PATCH.py';" ^
  "New-Item -ItemType Directory -Force -Path 'score2tab' | Out-Null;" ^
  "Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/lwp853/Test/score2tab-v0.2.2/score2tab-v0.2.2-patch/score2tab/bass_verify.py' -OutFile 'score2tab\bass_verify.py'"
if errorlevel 1 (
  echo.
  echo The patch files could not be downloaded. Check your internet connection and try again.
  echo.
  pause
  exit /b 1
)

set "PYTHON_LAUNCH=py -3"
where py >nul 2>nul
if errorlevel 1 set "PYTHON_LAUNCH=python"

echo Applying the patch...
%PYTHON_LAUNCH% APPLY_V022_PATCH.py
if errorlevel 1 (
  echo.
  echo The patch did not finish. Read the message above.
  echo.
  pause
  exit /b 1
)

echo.
echo Score2Tab v0.2.2 is ready.
echo Start it with RUN_SCORE2TAB.bat.
echo.
pause
exit /b 0
