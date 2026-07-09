@echo off
setlocal
cd /d C:\Users\LWH\Desktop\ultralytics-main
echo === 枸杞 v7 重训练 (baizhi GPU) ===
C:\Users\LWH\miniconda3\envs\baizhi\python.exe gouqi\scripts\retrain_v7.py --device 0 %*
if errorlevel 1 pause
exit /b %ERRORLEVEL%
