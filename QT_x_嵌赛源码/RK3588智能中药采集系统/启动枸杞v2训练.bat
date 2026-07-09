@echo off
chcp 65001 >nul
title 枸杞v2训练-提升置信度
cd /d "%~dp0"
set "PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe"
echo 步骤: 精修标注 + 旋转增强 + 训练 v2（约30分钟）
"%PY%" gouqi\scripts\retrain_v2.py --device 0 --batch 2
pause
