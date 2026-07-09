@echo off
chcp 65001 >nul
title 白芷检测 - 抗误检
cd /d "%~dp0"
set PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe
"%PY%" baizhi\scripts\detect_camera.py --device 0 --mode balanced --max-fps 10 --infer-every 2 --hold-ms 0 --box-shrink 0.65 --confirm 2 %*
pause
