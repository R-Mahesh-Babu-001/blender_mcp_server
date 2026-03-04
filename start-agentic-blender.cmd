@echo off
setlocal
set ROOT=C:\Users\gHOST\Downloads\New folder
start "" "%ROOT%\backend_runtime\Scripts\python.exe" "%ROOT%\scripts\workspace_boot.py"
start "" /D "C:\Program Files\Blender Foundation\Blender 5.0" blender.exe --python "%ROOT%\scripts\blender_startup.py"
endlocal
