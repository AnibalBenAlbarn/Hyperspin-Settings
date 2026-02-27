@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM =========================================================
REM CONFIGURA AQUÍ TUS RUTAS
REM =========================================================
set "ROMPATH=D:\ROMS\Sony PlayStation 3\1-ROMS"
set "OUTPATH=D:\ROMS\Sony PlayStation 3\4-JUEGOS TXT"

REM =========================================================
REM CREAR CARPETA DE SALIDA SI NO EXISTE
REM =========================================================
if not exist "%OUTPATH%" mkdir "%OUTPATH%"

echo.
echo =========================================================
echo  Creando TXT para carpetas en:
echo   ROMPATH = %ROMPATH%
echo   OUTPATH = %OUTPATH%
echo =========================================================
echo.

REM =========================================================
REM RECORRE CADA CARPETA DENTRO DE ROMPATH
REM Y CREA UN TXT CON EL MISMO NOMBRE EN OUTPATH
REM CONTENIDO DEL TXT: NOMBRE DE LA CARPETA (1 LINEA)
REM =========================================================
set /a COUNT=0

for /d %%D in ("%ROMPATH%\*") do (
    set "FOLDERNAME=%%~nxD"
    set "TXTFILE=%OUTPATH%\!FOLDERNAME!.txt"

    > "!TXTFILE!" echo !FOLDERNAME!
    set /a COUNT+=1
    echo [OK] "!TXTFILE!"
)

echo.
echo =========================================================
echo  Listo. TXT creados: %COUNT%
echo =========================================================
echo.
pause
endlocal
