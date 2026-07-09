@echo off
chcp 65001 >nul
title RK3588 FP16 模型导出 (WSL/虚拟机)
cd /d "%~dp0"
echo 导出 FP16 模型（推荐，INT8 易导致板端检不出）
echo.
wsl bash -lc "cd /mnt/c/Users/LWH/Desktop/ultralytics-main && bash rk3588/export_models_wsl.sh fp16" 2>nul
if errorlevel 1 (
  echo WSL 不可用，请在 Ubuntu 虚拟机中执行:
  echo   bash rk3588/export_models_wsl.sh fp16
)
pause
