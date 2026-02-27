@echo off
REM Nombre del archivo BAT
set "SELF=%~nx0"

REM Crear o sobreescribir lista.txt
echo Lista de archivos en %cd% > lista.txt
echo ========================= >> lista.txt

REM Recorre todos los archivos y excluye el BAT
for %%f in (*.*) do (
    if /I not "%%f"=="%SELF%" echo %%f >> lista.txt
)

echo Lista generada en lista.txt
pause
