@echo off
REM Mueve todos los archivos de las subcarpetas a la carpeta actual

for /r %%i in (*) do (
    if not "%%~pi"=="%cd%\" (
        move "%%i" "%cd%" >nul
    )
)

echo.
echo Todos los archivos han sido movidos a: %cd%
pause
