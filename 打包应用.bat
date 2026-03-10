@echo off
chcp 65001 >nul
echo ========================================
echo 打包 Windows 可执行程序
echo ========================================
echo.

cd /d "%~dp0"

echo [步骤1] 检查虚拟环境...
if not exist "venv\Scripts\activate.bat" (
    echo   ✗ 虚拟环境不存在
    echo   请先运行"快速测试.bat"或"重建虚拟环境.bat"
    pause
    exit /b 1
)
echo   ✓ 虚拟环境存在
echo.

echo [步骤2] 激活虚拟环境...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo   [错误] 无法激活虚拟环境
    pause
    exit /b 1
)
echo   ✓ 虚拟环境已激活
echo.

echo [步骤3] 检查 PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo   PyInstaller 未安装，正在安装...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo   [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
    echo   ✓ PyInstaller 已安装
) else (
    echo   ✓ PyInstaller 已安装
)
echo.

echo [步骤4] 清理旧的构建文件...
if exist "build" (
    echo   正在删除 build 目录...
    rmdir /s /q "build" 2>nul
)
if exist "dist" (
    echo   正在删除 dist 目录...
    rmdir /s /q "dist" 2>nul
)
echo   ✓ 清理完成
echo.

echo [步骤5] 开始打包（这可能需要几分钟）...
echo.
python build.py
if errorlevel 1 (
    echo.
    echo   [错误] 打包失败
    pause
    exit /b 1
)
echo.

echo ========================================
echo 打包完成！
echo ========================================
echo.
echo 可执行文件位置: dist\AutoEvalTool.exe
echo.
pause
