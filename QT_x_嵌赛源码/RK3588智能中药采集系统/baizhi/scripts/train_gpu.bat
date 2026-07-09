@echo off
REM 白芷 GPU 训练 - 强制使用 baizhi 环境 (RTX 5060 / sm_120)
cd /d "%~dp0..\.."
set PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe
if not exist "%PY%" (
    echo [错误] 未找到 baizhi 环境，请先运行: conda create -n baizhi python=3.11 -y
    pause
    exit /b 1
)
echo 使用: %PY%
"%PY%" baizhi/scripts/train.py --device 0 --batch 4 --workers 4 %*
pause
