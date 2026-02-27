@echo off
setlocal enabledelayedexpansion

echo ================================================
echo   Convertir .ISO a XISO usando extract-xiso.exe
echo ================================================
echo.
set /p folder=Introduce la ruta del directorio donde están los .iso: 

if not exist "%folder%" (
    echo La ruta no existe.
    pause
    exit /b
)

echo Buscando archivos .iso (excluyendo *.xiso.iso)...
echo.

for %%A in ("%folder%\*.iso") do (
    set file=%%~nxA

    rem Excluir archivos que terminen en .xiso.iso
    echo !file! | findstr /i "\.xiso\.iso$" >nul
    if errorlevel 1 (
        echo Procesando: %%A

        rem Obtener nombre base sin extensión
        set base=%%~nA

        rem Crear archivo XISO con extract-xiso.exe
        echo Ejecutando: extract-xiso.exe -c "%%~dpnA" "%folder%\!base!.xiso"
        extract-xiso.exe -c "%%~dpnA" "%folder%\!base!.xiso"
    ) else (
        echo Saltado (ya es un .xiso.iso): %%A
    )
)

echo.
echo Conversion finalizada.
pause
