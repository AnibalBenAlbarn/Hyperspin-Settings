@echo off
chcp 65001 >nul
title HyperSpin Video Cleaner

echo ==========================================
echo   HYPERSPIN VIDEO CLEANER (CON AUDIO)
echo ==========================================
echo.

:: PEDIR VIDEO DE ENTRADA
set /p INPUT=Ruta COMPLETA del video de ENTRADA (ej: C:\Videos\Namco.mp4):
echo.

if not exist "%INPUT%" (
    echo ERROR: El archivo no existe.
    pause
    exit /b
)

:: PEDIR CARPETA DE SALIDA
set /p OUTPUTDIR=Carpeta de SALIDA (ej: C:\Users\Anibal\Desktop):
echo.

if not exist "%OUTPUTDIR%" (
    echo ERROR: La carpeta no existe.
    pause
    exit /b
)

:: PEDIR NOMBRE FINAL
set /p OUTPUTNAME=Nombre FINAL del video (sin .mp4, ej: Namco System Super 23):
echo.

set OUTPUTFILE=%OUTPUTDIR%\%OUTPUTNAME%.mp4

echo ------------------------------------------
echo Procesando video...
echo Entrada : %INPUT%
echo Salida  : %OUTPUTFILE%
echo ------------------------------------------
echo.

ffmpeg -i "%INPUT%" ^
-map 0:v:0 -map 0:a:0 ^
-c:v libx264 -profile:v high -level 4.1 ^
-pix_fmt yuv420p -preset slow -crf 18 ^
-c:a aac -b:a 128k -ar 48000 -ac 2 ^
-movflags +faststart ^
"%OUTPUTFILE%"

echo.
echo ==========================================
echo   PROCESO FINALIZADO
echo ==========================================
echo Archivo creado:
echo %OUTPUTFILE%
echo.
pause
