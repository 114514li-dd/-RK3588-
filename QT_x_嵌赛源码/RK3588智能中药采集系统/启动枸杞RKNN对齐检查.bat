@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 检查 Windows 与 RKNN 应使用同一枸杞权重
C:\Users\LWH\miniconda3\envs\baizhi\python.exe rk3588\verify_gouqi_weights.py %*
pause
