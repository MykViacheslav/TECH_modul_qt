@echo off
setlocal
title TECH MODUL WEB - START
cd /d "%~dp0"

echo.
echo  ============================================
echo       TECH MODUL - WERSJA WEB
echo       Uruchamianie systemu...
echo  ============================================
echo.

powershell -ExecutionPolicy Bypass -File scripts\start_web_stack.ps1

if %errorlevel% neq 0 (
  echo.
  echo [BLAD] Nie udalo sie uruchomic systemu.
  pause
  exit /b %errorlevel%
)

echo.
echo  ============================================
echo       SYSTEM GOTOWY!
echo  ============================================
echo.
pause
