@echo off
rem ============================================
rem  TETRIS 3D RUSH 一键打包 EXE
rem  依赖：D:\tetris3d-venv 中已安装 pyinstaller
rem  产物：dist\Tetris3DRush.exe（单文件，无需 Python 环境）
rem  全程在 D 盘工作，不占用 C 盘空间
rem ============================================
setlocal
set VENV=D:\tetris3d-venv
set TMP=D:\tetris3d\pyi_tmp
set TEMP=D:\tetris3d\pyi_tmp
if not exist "%TMP%" mkdir "%TMP%"

if not exist "%VENV%\Scripts\pyinstaller.exe" (
    echo [setup] 安装 pyinstaller ...
    "%VENV%\Scripts\python.exe" -m pip install --no-cache-dir pyinstaller
)

cd /d "%~dp0"
"%VENV%\Scripts\pyinstaller.exe" --noconfirm --clean --onefile --windowed ^
    --name Tetris3DRush ^
    --distpath "%~dp0dist" ^
    --workpath "%~dp0build" ^
    --specpath "%~dp0build" ^
    main.py

echo.
echo 打包完成：dist\Tetris3DRush.exe
pause
