@echo off
setlocal
cd /d "%~dp0"
echo WhiteSur Monterey Adaptive - Firefox profile check
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-WhiteSur-Monterey-Adaptive.ps1" -Diagnose
set "EXITCODE=%ERRORLEVEL%"
echo.
if not "%EXITCODE%"=="0" echo The check failed with exit code %EXITCODE%.
pause
exit /b %EXITCODE%
