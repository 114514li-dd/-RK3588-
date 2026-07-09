@echo off

chcp 65001 >nul

setlocal enabledelayedexpansion



set IMAGE=

set PROMPT_FILE=

set MODE=gouqi



:parse

if "%~1"=="" goto run

if /i "%~1"=="--image" (

    set IMAGE=%~2

    shift & shift

    goto parse

)

if /i "%~1"=="--prompt-file" (

    set PROMPT_FILE=%~2

    shift & shift

    goto parse

)

if /i "%~1"=="--mode" (

    set MODE=%~2

    shift & shift

    goto parse

)

echo Unknown arg: %~1 >&2

exit /b 1



:run

if not exist "%IMAGE%" (

    echo Image not found: %IMAGE% >&2

    exit /b 2

)

if not exist "%PROMPT_FILE%" (

    echo Prompt file not found: %PROMPT_FILE% >&2

    exit /b 3

)



REM TODO: replace with real DeepSeek vision inference using IMAGE, PROMPT_FILE and MODE

if /i "%MODE%"=="object" (

    where python >nul 2>&1

    if !errorlevel! equ 0 (

        python "%~dp0object_recognize.py" "%IMAGE%"

        exit /b !errorlevel!

    )

    echo 【物品名称】未知物品

    echo 【物品类别】未知

    echo 【外观特征】演示环境未安装 Python/OpenCV，请配置真实 DeepSeek 视觉模型。

    echo 【详细描述】请在系统设置中部署板端 DeepSeek 推理程序后重试。

    exit /b 0

)



REM Gouqi demo (only for herb workflow)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^

  "[Console]::OutputEncoding=[Text.UTF8Encoding]::UTF8;" ^

  "Write-Output '【药品名称】宁夏枸杞（Lycium barbarum L.）';" ^

  "Write-Output '【药材分类】补阴药';" ^

  "Write-Output '【性味归经】甘，平。归肝、肾经';" ^

  "Write-Output '【功效】滋补肝肾，益精明目';" ^

  "Write-Output '【用法用量】6-12g，煎服；也可泡水、煲汤';" ^

  "Write-Output '【禁忌】脾虚便溏者慎用';" ^

  "Write-Output '【真伪鉴别要点】纺锤形或椭圆形，表面暗红色，具不规则皱纹，一端可见花柱残迹'"

exit /b 0

