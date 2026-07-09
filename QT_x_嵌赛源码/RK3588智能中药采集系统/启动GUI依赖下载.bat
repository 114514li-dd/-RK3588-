@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 在有网的 WSL/Linux 中下载 aarch64 whl，然后上传到板子 rk3588/offline_wheels/
wsl bash rk3588/download_gui_wheels_pc.sh
pause
