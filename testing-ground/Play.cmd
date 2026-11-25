@echo off
setlocal
cd /d "%~dp0"
if exist "engine\Godot_v4.7.2-stable_win64.exe" (
  echo Preparing character assets...
  start /wait "Importing characters" "engine\Godot_v4.7.2-stable_win64.exe" --headless --editor --import --path "%~dp0." --log-file "%~dp0import.log"
  start "Character Creations" "engine\Godot_v4.7.2-stable_win64.exe" --path "%~dp0." --log-file "%~dp0testing-ground.log"
) else (
  echo Open project.godot with Godot 4.7.2 or newer, then press F6 on main.tscn.
  echo The downloadable Windows package includes the engine and launches directly.
  pause
)
