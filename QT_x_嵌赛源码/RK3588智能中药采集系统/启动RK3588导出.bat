@echo off
chcp 65001 >nul
title RK3588 模型导出 (WSL)
cd /d "%~dp0"

echo 在 WSL2 Ubuntu 中执行 RKNN 导出 (Windows 无法直接转 RKNN)
echo.
wsl bash -lc "cd /mnt/c/Users/LWH/Desktop/ultralytics-main && bash rk3588/export_models_wsl.sh"
pause
