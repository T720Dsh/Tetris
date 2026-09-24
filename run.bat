@echo off
rem ============================================
rem  TETRIS 3D RUSH 启动器
rem  虚拟环境默认建在 D:\tetris3d-venv
rem  （避开本机 C 盘空间紧张；代码仍在项目目录）
rem ============================================
set VENV=D:\tetris3d-venv
if not exist "%VENV%\Scripts\python.exe" (
    echo [setup] 未找到虚拟环境 %VENV%，正在创建并安装依赖...
    where py >nul 2>nul && (py -3.12 -m venv "%VENV%") || (python -m venv "%VENV%")
    if errorlevel 1 (
        echo [error] 虚拟环境创建失败，请手动安装 Python 3.12 后重试。
        pause
        exit /b 1
    )
    "%VENV%\Scripts\python.exe" -m pip install --no-cache-dir -r "%~dp0requirements.txt"
)
cd /d "%~dp0"
"%VENV%\Scripts\python.exe" main.py
