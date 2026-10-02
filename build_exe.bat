@echo off
setlocal enableextensions enabledelayedexpansion

echo ========================================================
echo         Building pst2mbox Standalone Executable
echo ========================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ❌ Python was not found in PATH.
    echo Please install Python 3.8+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found. Running build script...
python build_exe.py

if errorlevel 1 (
    echo.
    echo ❌ Build encountered an error.
) else (
    echo.
    echo ✓ Build finished! Check the dist\ folder for pst2mbox.exe
)
echo.
pause
