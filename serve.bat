@echo off
title Problem Forge
cd /d "%~dp0"

echo ============================================================
echo                 PROBLEM FORGE
echo ============================================================
echo.
echo Updating the problem catalog before starting...
echo This can take a few minutes the first time because it fetches
echo thousands of problem records from the public catalogs.
echo.

python update_catalog.py
if errorlevel 1 (
  echo.
  echo WARNING: Catalog refresh did not fully succeed.
  echo The site will still start using the latest catalog available.
  echo.
)

echo.
echo Starting local server...
echo Open: http://localhost:8000
echo.
echo Keep this window open while using the website.
echo Press Ctrl+C to stop the server.
echo.
python -m http.server 8000
