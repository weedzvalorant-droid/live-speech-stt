@echo off
setlocal

echo === Live Speech STT: installation ===

set PYCMD=
py -3.12 --version >nul 2>nul
if not errorlevel 1 set PYCMD=py -3.12
if defined PYCMD goto havepy

py -3.11 --version >nul 2>nul
if not errorlevel 1 set PYCMD=py -3.11
if defined PYCMD goto havepy

py -3.10 --version >nul 2>nul
if not errorlevel 1 set PYCMD=py -3.10
if defined PYCMD goto havepy

where python >nul 2>nul
if errorlevel 1 goto nopython
set PYCMD=python

:havepy
echo Using interpreter: %PYCMD%

if exist venv goto havevenv
echo Creating virtual environment...
%PYCMD% -m venv venv
:havevenv

call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 goto pipupgradefail

echo Installing dependencies (this can take a few minutes, especially the first time)...
pip install -r requirements.txt
if errorlevel 1 goto pipinstallfail

echo.
echo === Installation complete ===
echo Run the app with: run.bat
pause
exit /b 0

:nopython
echo [ERROR] No compatible Python found (need 3.10, 3.11 or 3.12, 64-bit).
echo Install it from python.org, then run this script again.
pause
exit /b 1

:pipupgradefail
echo [ERROR] Failed to upgrade pip, see output above.
pause
exit /b 1

:pipinstallfail
echo [ERROR] Failed to install dependencies, see output above.
pause
exit /b 1
