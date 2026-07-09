@echo off
chcp 65001 >nul
title 枸杞 v6 实拍过采样微调
cd /d "%~dp0"
set "PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe"
echo v6: 实拍图过采样 x40 + 25轮微调（约 15~25 分钟）
echo 基于 v5 权重，输出 gouqi/runs/detect/gouqi_yolov8s_ca_v6/weights/best.pt
"%PY%" gouqi\scripts\finetune_real_boost.py --device 0 --copies 40 --epochs 25 --batch 2 --workers 0
pause
