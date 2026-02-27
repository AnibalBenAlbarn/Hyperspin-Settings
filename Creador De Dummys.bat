@echo off
setlocal

rem Crear carpeta "Bat dummys" si no existe
if not exist "Bat dummys" (
    mkdir "Bat dummys"
)

rem Recorre SOLO las carpetas del directorio actual
for /D %%D in (*) do (
    rem Evitar que procese la carpeta "Bat dummys"
    if /I not "%%D"=="Bat dummys" (
        echo Creando "Bat dummys\%%D.bat"
        (
            echo @echo off
            echo rem Dummy para %%D
        )>"Bat dummys\%%D.bat"
    )
)

echo.
echo Terminado. Los .bat están en la carpeta "Bat dummys".
pause
