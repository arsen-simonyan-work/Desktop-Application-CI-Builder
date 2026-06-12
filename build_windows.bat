@echo off
setlocal

py -3 -m pip install --upgrade pip
if exist requirements.txt py -3 -m pip install -r requirements.txt
py -3 -m pip install pyinstaller pillow
py -3 scripts\generate_icons.py --require-icns

py -3 -m PyInstaller DesktopAppCiBuilder.spec --noconfirm --clean
if errorlevel 1 exit /b 1

echo Build complete
