@echo off
cd /d "%~dp0"
set "PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe"
echo baizhi v4 real boost (~3 min)
"%PY%" baizhi\scripts\finetune_real_boost.py --device 0 --workers 0 --batch 4 --turbo
pause
