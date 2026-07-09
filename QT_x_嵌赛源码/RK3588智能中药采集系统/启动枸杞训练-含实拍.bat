@echo off
chcp 65001 >nul
title 枸杞训练-含实拍 v5
cd /d "%~dp0"
set "PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe"
echo 快速微调 v5（约 10~15 分钟）
"%PY%" gouqi\scripts\train_with_user_images.py --device 0 --workers 0 --fast --skip-import
pause
