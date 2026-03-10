@echo off
chcp 65001 >nul
echo ========================================
echo 检查虚拟环境状态
echo ========================================
echo.

cd /d "%~dp0"

echo [检查1] venv 文件夹是否存在...
if exist "venv" (
    echo   ✓ venv 文件夹存在
) else (
    echo   ✗ venv 文件夹不存在
    echo   需要运行"重建虚拟环境.bat"
    pause
    exit /b 1
)
echo.

echo [检查2] activate.bat 是否存在...
if exist "venv\Scripts\activate.bat" (
    echo   ✓ activate.bat 存在
) else (
    echo   ✗ activate.bat 不存在
    echo   虚拟环境不完整，需要重建
    pause
    exit /b 1
)
echo.

echo [检查3] python.exe 是否存在...
if exist "venv\Scripts\python.exe" (
    echo   ✓ python.exe 存在
) else (
    echo   ✗ python.exe 不存在
    echo   虚拟环境不完整，需要重建
    pause
    exit /b 1
)
echo.

echo [检查4] 尝试激活虚拟环境...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo   ✗ 激活失败
    echo   虚拟环境可能损坏，需要重建
    pause
    exit /b 1
) else (
    echo   ✓ 激活成功
)
echo.

echo [检查5] 检查 Python 版本...
python --version
if errorlevel 1 (
    echo   ✗ Python 无法运行
) else (
    echo   ✓ Python 正常
)
echo.

echo [检查6] 检查已安装的包...
python -m pip list | findstr /i "streamlit pandas openpyxl"
if errorlevel 1 (
    echo   ✗ 缺少必要的包
    echo   需要运行: pip install streamlit pandas openpyxl
) else (
    echo   ✓ 必要的包已安装
)
echo.

echo ========================================
echo 检查完成
echo ========================================
echo.
pause
