@echo off
chcp 65001 >nul
title 白芷训练 (baizhi GPU)
cd /d "%~dp0"
set PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe

if not exist "%PY%" (
    echo [错误] 未找到 baizhi 环境
    pause
    exit /b 1
)

echo ========================================
echo  白芷模型训练 (RTX 5060 / baizhi 环境)
echo ========================================
"%PY%" baizhi\scripts\train.py --device 0 --batch 2 --workers 2 --name baizhi_yolov8s_ca_v2 %*
pause
