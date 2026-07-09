@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe
"%PY%" herbs2/scripts/merge_dataset.py
"%PY%" herbs2/scripts/train.py --device 0 --batch 2 --skip-merge
pause
