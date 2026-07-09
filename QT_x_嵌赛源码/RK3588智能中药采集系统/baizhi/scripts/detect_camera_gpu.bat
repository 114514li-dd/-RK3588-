@echo off
REM 白芷摄像头检测 - 强制使用 baizhi 环境 (RTX 5060)
cd /d "%~dp0..\.."
set PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe
if not exist "%PY%" (
    echo [错误] 未找到 baizhi 环境，请先: conda activate baizhi
    pause
    exit /b 1
)
echo 使用: %PY%
"%PY%" baizhi/scripts/detect_camera.py --device 0 --mode balanced --max-fps 10 --infer-every 2 %*
pause
