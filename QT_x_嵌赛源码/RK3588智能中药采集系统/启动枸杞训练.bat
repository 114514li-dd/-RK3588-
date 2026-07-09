@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe
"%PY%" gouqi\scripts\import_dataset.py
"%PY%" gouqi\scripts\import_negatives.py
"%PY%" gouqi\scripts\train.py --device 0 --batch 2
pause
