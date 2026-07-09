@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."
set PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe
if not exist "%PY%" (
    echo [错误] 未找到 baizhi 环境
    pause
    exit /b 1
)
"%PY%" herbs2/scripts/train.py --device 0 --batch 2 %*
pause
