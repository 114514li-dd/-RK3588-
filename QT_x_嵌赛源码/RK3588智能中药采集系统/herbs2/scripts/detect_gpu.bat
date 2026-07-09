@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."
set "PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe"
"%PY%" herbs2\scripts\detect_camera.py --device 0 --backend ensemble --debug %*
pause
