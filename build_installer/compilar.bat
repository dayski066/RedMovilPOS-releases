@echo off
REM ============================================================
REM Script para compilar RedMovilPOS a ejecutable
REM ============================================================

echo ============================================================
echo   COMPILACION DE REDMOVILPOS
echo ============================================================
echo.

REM Cambiar al directorio del proyecto
cd /d "%~dp0.."

REM Limpiar compilaciones anteriores
echo Limpiando compilaciones anteriores...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
echo [OK] Limpieza completada
echo.

REM Ejecutar PyInstaller
echo Compilando con PyInstaller...
echo (Esto puede tardar varios minutos)
echo.

python -m PyInstaller build_installer\RedMovilPOS.spec --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] La compilacion fallo
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   COMPILACION COMPLETADA
echo ============================================================
echo.
echo El ejecutable se encuentra en: dist\RedMovilPOS\
echo.
echo Archivo principal: dist\RedMovilPOS\RedMovilPOS.exe
echo.

REM Abrir carpeta de salida
explorer "dist\RedMovilPOS"

pause
