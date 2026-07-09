@echo off
cd /d "%~dp0"
set "PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe"
if not exist "%PY%" (
    echo ERROR: baizhi python not found: %PY%
    pause
    exit /b 1
)
echo Dir: %CD%
"%PY%" herbs2\scripts\detect_camera.py --device 0 --backend ensemble --infer-every 3 --max-fps 20 --hold-ms 0 --confirm-baizhi 2 --conf-baizhi 0.50 %*
pause
