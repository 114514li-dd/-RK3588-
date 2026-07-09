@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo 演示模式（PC 无 RKNN，仅预览界面布局）
python rk3588\gui\app.py --demo --camera 0
pause
