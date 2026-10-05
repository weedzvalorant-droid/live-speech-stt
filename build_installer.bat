@echo off
setlocal

if exist "dist\LiveSpeechSTT\LiveSpeechSTT.exe" goto havebuilt
echo [ERROR] dist\LiveSpeechSTT\LiveSpeechSTT.exe not found. Run build.bat first.
pause
exit /b 1

:havebuilt
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist %ISCC% goto haveiscc

set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist %ISCC% goto haveiscc

echo [ERROR] Inno Setup 6 not found.
echo Install it (free) from https://jrsoftware.org/isdl.php and run this script again.
pause
exit /b 1

:haveiscc
echo Building installer with %ISCC% ...
%ISCC% installer.iss
if errorlevel 1 goto buildfailed

echo.
echo === Installer built ===
echo See: installer_output\LiveSpeechSTT-Setup-1.0.0.exe
pause
exit /b 0

:buildfailed
echo [ERROR] Inno Setup compilation failed, see output above.
pause
exit /b 1
