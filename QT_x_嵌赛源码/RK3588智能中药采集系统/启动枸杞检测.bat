@echo off
chcp 65001 >nul
title 枸杞检测 - Windows GPU
cd /d "%~dp0"

echo ========================================
echo  Windows 本地检测 (需 RTX GPU + baizhi 环境)
echo  板端参数已对齐 Windows balanced (conf=0.40 shrink=0.65)
echo  RKNN 导出请在 PC 双击: 启动RK3588导出FP16.bat（勿在板子上 export）
echo  板端推理: bash rk3588/启动枸杞检测.sh
echo ========================================
echo.

set PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe
if not exist "%PY%" (
    echo [错误] 未找到 %PY%
    pause
    exit /b 1
)

"%PY%" gouqi\scripts\detect_camera.py --device 0 --mode balanced --infer-every 3 --max-fps 20 --box-shrink 0.65 %*
pause
