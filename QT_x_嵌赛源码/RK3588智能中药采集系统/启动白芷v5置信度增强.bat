@echo off
cd /d "%~dp0"
set "PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe"
echo baizhi v5 finetune from v4 (~8 min, skip oversample)
"%PY%" baizhi\scripts\finetune_real_boost.py --device 0 --workers 0 --batch 4 --skip-oversample --epochs 20 --patience 8 --name baizhi_yolov8s_ca_v5 --cls 1.0
pause
