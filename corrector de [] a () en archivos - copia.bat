@echo off
setlocal EnableDelayedExpansion

rem ===== CARPETAS (de más profundas a más altas) =====
for /f "delims=" %%D in ('dir /b /s /ad ^| sort /r') do (
    set "old=%%~nxD"
    set "new=!old:[=(!"
    set "new=!new:]=)!"
    if not "!old!"=="!new!" (
        ren "%%D" "!new!"
    )
)

rem ===== ARCHIVOS =====
for /f "delims=" %%F in ('dir /b /s /a-d') do (
    set "old=%%~nxF"
    set "new=!old:[=(!"
    set "new=!new:]=)!"
    if not "!old!"=="!new!" (
        ren "%%F" "!new!"
    )
)

echo Proceso terminado.
pause
