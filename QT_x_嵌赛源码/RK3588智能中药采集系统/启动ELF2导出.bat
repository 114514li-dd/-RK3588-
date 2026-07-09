@echo off
chcp 65001 >nul
title 白芷 ELF2 导出 ONNX
cd /d "%~dp0"
set PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe
"%PY%" baizhi\scripts\export_elf2.py %*
pause
