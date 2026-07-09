@echo off
chcp 65001 >nul
title 白芷检测 - 严格抗误检
cd /d "%~dp0"
set PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe
"%PY%" baizhi\scripts\detect_camera.py --device 0 --mode strict %*
pause
