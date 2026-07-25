@echo off
setlocal EnableExtensions

set "HERE=%~dp0"
set "APP_ROOT="

if exist "%HERE%score2tab\app.py" set "APP_ROOT=%HERE%"
if exist "%HERE%..\score2tab\app.py" set "APP_ROOT=%HERE%.."

if not defined APP_ROOT (
  echo.
  echo Score2Tab Hotfix 2 rollback
  echo ===========================
  echo.
  echo Put this file either in the main Score2Tab folder or in its Updates folder.
  echo I could not find score2tab\app.py near:
  echo %HERE%
  echo.
  pause
  exit /b 1
)

for %%I in ("%APP_ROOT%") do set "APP_ROOT=%%~fI"
cd /d "%APP_ROOT%"

set "BACKUP_DIR="
for /f "delims=" %%D in ('dir /b /ad /o-n "Updates\Backups\v0.2.2-hotfix2-*" 2^>nul') do (
  if not defined BACKUP_DIR set "BACKUP_DIR=Updates\Backups\%%D"
)

if not defined BACKUP_DIR (
  echo.
  echo No Hotfix 2 backup was found under:
  echo %APP_ROOT%\Updates\Backups
  echo.
  echo Nothing was changed.
  pause
  exit /b 1
)

echo.
echo Score2Tab Hotfix 2 rollback
 echo ===========================
echo.
echo Restoring from:
echo %APP_ROOT%\%BACKUP_DIR%
echo.

for %%F in (app.py bass_verify.py musicxml.py report.py) do (
  if exist "%BACKUP_DIR%\score2tab\%%F" (
    copy /y "%BACKUP_DIR%\score2tab\%%F" "score2tab\%%F" >nul
    if errorlevel 1 goto :failed
    echo Restored score2tab\%%F
  )
)

if exist ".venv\Scripts\python.exe" (
  echo.
  echo Checking that Score2Tab imports correctly...
  ".venv\Scripts\python.exe" -c "import score2tab; import score2tab.app; print('Score2Tab import check passed:', score2tab.__version__)"
  if errorlevel 1 goto :failed
)

echo.
echo Rollback complete. Score2Tab is back at the state immediately before Hotfix 2.
echo Start it using RUN_SCORE2TAB.bat from the main Score2Tab folder.
echo.
pause
exit /b 0

:failed
echo.
echo The rollback did not complete successfully.
echo Do not delete the Updates\Backups folder.
echo.
pause
exit /b 1
