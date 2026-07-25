@echo off
setlocal

set "HERE=%~dp0"
set "APP_ROOT="

if exist "%HERE%score2tab\app.py" set "APP_ROOT=%HERE%"
if exist "%HERE%..\score2tab\app.py" set "APP_ROOT=%HERE%.."

if not defined APP_ROOT (
  echo.
  echo Score2Tab v0.2.2 hotfix 2
  echo =============================
  echo.
  echo Store this installer either:
  echo   1. in the main Score2Tab folder, or
  echo   2. in a folder named Updates directly inside Score2Tab.
  echo.
  echo I could not find score2tab\app.py near:
  echo %HERE%
  echo.
  pause
  exit /b 1
)

for %%I in ("%APP_ROOT%") do set "APP_ROOT=%%~fI"
cd /d "%APP_ROOT%"

if not exist "Updates" mkdir "Updates"

echo.
echo Score2Tab v0.2.2 hotfix 2
 echo =============================
echo.
echo App folder: %APP_ROOT%
echo.

where powershell >nul 2>nul
if errorlevel 1 (
  echo PowerShell was not found.
  pause
  exit /b 1
)

echo Downloading the hotfix patcher...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop'; Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/lwp853/Test/score2tab-v0.2.2/score2tab-v0.2.2-patch/HOTFIX_V022_2.py' -OutFile 'Updates\HOTFIX_V022_2.py'"
if errorlevel 1 (
  echo.
  echo The hotfix could not be downloaded. Check your internet connection.
  echo.
  pause
  exit /b 1
)

echo Applying hotfix 2...
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "Updates\HOTFIX_V022_2.py"
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 "Updates\HOTFIX_V022_2.py"
  ) else (
    python "Updates\HOTFIX_V022_2.py"
  )
)

if errorlevel 1 (
  echo.
  echo The hotfix did not finish. Read the message above.
  echo No edited source file is kept without a backup.
  echo.
  pause
  exit /b 1
)

echo.
echo Hotfix 2 is installed.
echo Start Score2Tab with RUN_SCORE2TAB.bat.
echo.
echo Keep this installer in the Updates folder for your records.
echo.
pause
exit /b 0
