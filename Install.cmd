@echo off
setlocal
cd /d "%~dp0"
set "WHITESUR_SCRIPT=%~dp0Install-WhiteSur-Monterey-Adaptive.ps1"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath $env:WHITESUR_SCRIPT -ErrorAction SilentlyContinue"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%WHITESUR_SCRIPT%"
set "exitCode=%ERRORLEVEL%"
echo.
if not "%exitCode%"=="0" echo Installation failed with exit code %exitCode%.
pause
exit /b %exitCode%
