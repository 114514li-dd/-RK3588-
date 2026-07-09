@echo off
cd /d "%~dp0"
set "PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe"
echo baizhi v3 turbo (~2 min, 6 epochs)
"%PY%" baizhi\scripts\train_with_user_images.py --device 0 --workers 0 --turbo
pause
