@echo off
cd /d "%~dp0"
set "PY=C:\Users\LWH\miniconda3\envs\baizhi\python.exe"
set "AS=C:\Users\LWH\.cursor\projects\c-Users-LWH-Desktop-ultralytics-main\assets"
echo import user photos + baizhi v6 finetune
"%PY%" baizhi\scripts\import_user_images.py ^
  "%AS%\c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_a4305acf99c147718f0c8024d0c295e3-532e5c65-5d87-4522-870c-ed7556183539.png" ^
  "%AS%\c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_c2d2a92a8897ea5ead63a368f0ab24ad-96f73d10-05ef-4e4a-b988-2a9a6239b2e8.png" ^
  "%AS%\c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_6e86ad21f74450c784ee6c7f4c4bd82f-27c45ea7-83e4-4e29-8637-e5fd73fb497a.png" ^
  "%AS%\c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_1530d149dd09ea37c5c297212df69252-9ffe73cc-8036-4145-b6ed-e12b7d224732.png" ^
  "%AS%\c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_ef5ddb0a36fbef9bd40160a606bfa640-959de751-4b25-4d80-9d06-77e1b9873f0a.png" ^
  "%AS%\c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_ccf54a601514c4ade349391878570a80-079706bf-4e9e-49be-8eaa-3d9fedf2fc62.png"
if errorlevel 1 pause & exit /b 1
"%PY%" baizhi\scripts\finetune_real_boost.py --device 0 --workers 0 --batch 4 --base baizhi\runs\detect\baizhi_yolov8s_ca_v5\weights\best.pt --name baizhi_yolov8s_ca_v6 --epochs 20 --patience 8 --cls 1.0 --copies 40
pause
