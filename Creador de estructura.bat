@echo off
setlocal enableextensions

rem ======= RAÍZ (directorio donde esté el .bat) =======
set "ROOT=%~dp0"
rem quitamos la barra final si la hay
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo Creando estructura en: "%ROOT%"
echo(

rem =========================================================================== 
rem NIVEL 1
rem ===========================================================================
mkdir "%ROOT%\1-HYPERSPIN" 2>nul
mkdir "%ROOT%\2-ROMS" 2>nul
mkdir "%ROOT%\3-EMULADORES" 2>nul
mkdir "%ROOT%\4-PC" 2>nul
mkdir "%ROOT%\5-UTILIDADES" 2>nul


rem =========================================================================== 
rem 2-ROMS
rem ===========================================================================
mkdir "%ROOT%\2-ROMS\1-PLACAS ARCADE" 2>nul
mkdir "%ROOT%\2-ROMS\2-SOBREMESA" 2>nul
mkdir "%ROOT%\2-ROMS\3-PORTATILES" 2>nul
mkdir "%ROOT%\2-ROMS\LIGHTGUN GAMES" 2>nul
mkdir "%ROOT%\2-ROMS\PELICULAS" 2>nul

rem -- 2-ROMS\1-PLACAS ARCADE
for %%D in (
"AAE"
"Atomiswave"
"Capcom 68000"
"Capcom Play System I"
"Capcom Play System II"
"Capcom Play System III"
"Capcom Section Z"
"CAVE"
"Chihiro"
"Irem M92"
"MetalSlug collection"
"Midway"
"Namco System 11"
"Namco System 12"
"Namco System 21"
"Namco System 22"
"Namco System 23"
"Namco System 246-256"
"Naomi"
"Neo Geo 64"
"Sega Mega Play"
"Sega Mega Tech System"
"Sega Model 1"
"Sega Model 2"
"Sega Model 3"
"Sega ST-V"
"Sega System 16"
"Sega System 18"
"Sega System 24"
"Sega System 32"
"Sega Triforce"
"Taito 68000"
"Taito 68020"
"Taito B System"
"Taito Birdie King"
"Taito Bonze Adventure"
"Taito Darius 2 Twin Screen"
"Taito F1 System"
"Taito FX-1A System"
"Taito FX-1B System"
"Taito H System"
"Taito L System"
"Taito Qix"
"Taito Safari"
"Taito System SJ"
"Taito Z System"
"Taito Z80"
"TEKNOPARROT"
"Zinc"
) do mkdir "%ROOT%\2-ROMS\1-PLACAS ARCADE\%%~D" 2>nul

rem -- 2-ROMS\2-SOBREMESA
for %%D in (
"Atari Jaguar"
"Microsoft XBOX"
"Microsoft XBOX 360"
"Nintendo 64"
"Nintendo GameCube"
"Nintendo NES"
"Nintendo NES ESP"
"Nintendo SNES"
"Nintendo SNES ESP"
"Nintendo Switch"
"Nintendo Wii"
"Nintendo Wii U"
"Scumm"
"Sega Dreamcast"
"Sega Genesis"
"Sega Genesis 32X"
"Sega Genesis CD"
"Sega MasterSystem"
"Sony PlayStation"
"Sony PlayStation 2"
"Sony PlayStation 3"
) do mkdir "%ROOT%\2-ROMS\2-SOBREMESA\%%~D" 2>nul

rem -- 2-ROMS\3-PORTATILES
for %%D in (
"Nintendo 3DS"
"Nintendo DS"
"Nintendo GameBoy Advance"
"Nintendo Gameboy Advance ESP"
"Nintendo GameBoy Color"
"Sega GameGear"
"SNK Neo Geo Pocket Color"
"Sony PlayStation Portable"
"Sony PlayStation Vita"
) do mkdir "%ROOT%\2-ROMS\3-PORTATILES\%%~D" 2>nul

rem -- 2-ROMS\LIGHTGUN GAMES
for %%D in (
"ARCADE"
"ARCADE MODERNO"
"CONSOLAS"
"PC"
) do mkdir "%ROOT%\2-ROMS\LIGHTGUN GAMES\%%~D" 2>nul

rem -- 2-ROMS\LIGHTGUN GAMES\ARCADE
for %%D in (
"ATOMISWAVE"
"MAME"
"NAMCO SYSTEM 246-256"
"SEGA MODEL 2"
"SEGA MODEL 3"
"SEGA NAOMI"
) do mkdir "%ROOT%\2-ROMS\LIGHTGUN GAMES\ARCADE\%%~D" 2>nul

rem -- 2-ROMS\LIGHTGUN GAMES\CONSOLAS
for %%D in (
"Nintendo WII"
"Sega Dreamcast"
"Sony PlayStation"
"Sony PlayStation 2"
"Sony PlayStation 3"
) do mkdir "%ROOT%\2-ROMS\LIGHTGUN GAMES\CONSOLAS\%%~D" 2>nul


rem =========================================================================== 
rem 3-EMULADORES
rem ===========================================================================
mkdir "%ROOT%\3-EMULADORES\1-PLACAS ARCADE" 2>nul
mkdir "%ROOT%\3-EMULADORES\2-SOBREMESA" 2>nul
mkdir "%ROOT%\3-EMULADORES\3-PORTATILES" 2>nul
mkdir "%ROOT%\3-EMULADORES\4-LIGHTGUN" 2>nul
mkdir "%ROOT%\3-EMULADORES\saves" 2>nul

rem -- 3-EMULADORES\1-PLACAS ARCADE
for %%D in (
"1-MAME"
"2-MAME OLD"
"3-ARCADE64"
"Atomiswave"
"Chihiro"
"Daphne"
"Naomi"
"Sega Model 2"
"Sega Model 3"
"TEKNOPARROT"
) do mkdir "%ROOT%\3-EMULADORES\1-PLACAS ARCADE\%%~D" 2>nul

rem -- 3-EMULADORES\2-SOBREMESA
for %%D in (
"Atari Jaguar"
"Microsoft XBOX"
"Microsoft XBOX 360"
"Nintendo 64"
"Nintendo GameCube"
"Nintendo NES"
"Nintendo SNES"
"Nintendo Switch"
"Nintendo Wii"
"Nintendo Wii U"
"Scumm"
"Sega Dreamcast"
"Sega Genesis"
"Sega MasterSystem"
"Sony PlayStation"
"Sony PlayStation 2"
"Sony PlayStation 3"
) do mkdir "%ROOT%\3-EMULADORES\2-SOBREMESA\%%~D" 2>nul

rem -- 3-EMULADORES\3-PORTATILES
for %%D in (
"Nintendo 3DS"
"Nintendo DS"
"Nintendo GB-GBC-GBA"
"SNK Neo Geo Pocket"
"Sony PlayStation Portable"
"Sony PlayStation Vita"
) do mkdir "%ROOT%\3-EMULADORES\3-PORTATILES\%%~D" 2>nul


echo.
echo ✓ Estructura creada/actualizada en: "%ROOT%"
echo (Las carpetas existentes se han respetado.)
pause
