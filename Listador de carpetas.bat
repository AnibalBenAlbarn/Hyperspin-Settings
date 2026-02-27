@echo off
setlocal

cd /d "%~dp0"

set "salida=lista_carpetas.txt"

dir /ad /b > "%salida%"

echo Lista guardada en %salida%
pause
