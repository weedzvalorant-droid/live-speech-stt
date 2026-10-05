@echo off
setlocal

if exist venv goto havevenv
echo Virtual environment not found. Run install.bat first.
pause
exit /b 1

:havevenv
call venv\Scripts\activate.bat

echo Building LiveSpeechSTT.exe with PyInstaller...
pyinstaller --name LiveSpeechSTT --windowed --onedir --noconfirm ^
    --icon=assets\icon.ico ^
    --add-data "assets;assets" ^
    --additional-hooks-dir=pyinstaller_hooks ^
    --collect-all faster_whisper ^
    --collect-all ctranslate2 ^
    --collect-all pyaudiowpatch ^
    --hidden-import=webrtcvad ^
    --hidden-import=pynput.keyboard._win32 ^
    --hidden-import=pynput.mouse._win32 ^
    main.py
if errorlevel 1 goto buildfailed

echo.
echo === Build complete ===
echo Executable: dist\LiveSpeechSTT\LiveSpeechSTT.exe
pause
exit /b 0

:buildfailed
echo [ERROR] PyInstaller build failed, see output above.
pause
exit /b 1
