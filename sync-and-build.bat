@echo off
title Problem Forge - Full Catalog Sync
cd /d "%~dp0"
python update_catalog.py
echo.
echo Finished. Press any key to close.
pause >nul
