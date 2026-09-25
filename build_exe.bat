@echo off
REM Tetris 3D Rush - Godot 导出脚本（模板与用户数据均在 D 盘）
setlocal
set GODOT="D:\Godot\Godot_v4.3-stable_win64.exe"
set PROJ=D:\GodotTetris3D
set APPDATA=D:\GodotAppData
set OUT=%PROJ%\build\Tetris3DRush.exe

if not exist "%APPDATA%\Godot\export_templates\4.3.stable\windows_release.exe" (
    echo [ERROR] 模板未就绪：%APPDATA%\Godot\export_templates\4.3.stable\
    exit /b 1
)

mkdir "%PROJ%\build" 2>nul
echo [1/2] 导出 Windows x86_64 可执行文件...
%GODOT% --headless --path "%PROJ%" --export-release "Windows Desktop" "%OUT%"
if errorlevel 1 (
    echo [ERROR] 导出失败
    exit /b 1
)
echo [2/2] 打包 zip...
powershell -NoProfile -Command "Compress-Archive -Path '%OUT%' -DestinationPath '%PROJ%\build\Tetris3DRush-win64.zip' -Force"
echo 完成：%OUT%
