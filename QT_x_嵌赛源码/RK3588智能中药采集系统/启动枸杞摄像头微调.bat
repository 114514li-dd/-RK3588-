@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe"
echo 步骤1: 摄像头采集枸杞样本（按空格保存，建议30张）
"%PY%" gouqi\scripts\collect_camera_samples.py --camera 0 --frames 30
echo.
echo 步骤2: 微调训练（提升摄像头置信度）
"%PY%" gouqi\scripts\finetune_camera.py --device 0 --batch 2
pause
