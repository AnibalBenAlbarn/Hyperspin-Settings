@echo off
setlocal EnableDelayedExpansion

REM ===== CONFIGURACIÓN =====
set "INI_FILE=E:\ARCADE\1-HYPERSPIN\RocketLauncher\Modules\PCLauncher\Sony PlayStation 3.ini"
set "GAMES_DIR=D:\ROMS\Sony PlayStation 3\2-JUEGOS BAT"
REM =========================

REM Borra el INI si ya existe
if exist "%INI_FILE%" del "%INI_FILE%"

REM Recorre todos los .bat de juegos
for %%F in ("%GAMES_DIR%\*.bat") do (
    echo [%%~nF]>>"%INI_FILE%"
    echo Application=%GAMES_DIR%\%%~nxF>>"%INI_FILE%"
    echo ExitMethod=Send Alt+F4>>"%INI_FILE%"
    echo.>>"%INI_FILE%"
)

echo.
echo INI generado correctamente con ExitMethod.
echo %INI_FILE%
pause
