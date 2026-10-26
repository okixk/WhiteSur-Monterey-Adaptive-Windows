@echo off
setlocal
call "%~dp0Install.cmd" -ClassicToolbar %*
exit /b %ERRORLEVEL%
