@echo off
setlocal

if exist venv goto havevenv
echo Virtual environment not found. Run install.bat first.
pause
exit /b 1

:havevenv
call venv\Scripts\activate.bat
python main.py
if errorlevel 1 goto appfailed

pause
exit /b 0

:appfailed
echo.
echo [ERROR] The app exited with an error, see output above.
pause
exit /b 1
