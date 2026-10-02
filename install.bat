@echo off
echo ============================================
echo         pst2mbox - Setup & Install
echo ============================================
echo.

echo Installing pst2mbox in current Python environment...
pip install -e .

echo.
echo Testing installation...
pst2mbox --help

echo.
echo Installation complete!
echo.
echo Usage:
echo   pst2mbox "your-file.pst" "output.mbox"
echo.
echo Or build a standalone .exe:
echo   build_exe.bat
echo.
pause