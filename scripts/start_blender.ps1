$blender = "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
$script = Join-Path $PSScriptRoot "blender_startup.py"
Start-Process -FilePath $blender -ArgumentList @("--python", $script)
