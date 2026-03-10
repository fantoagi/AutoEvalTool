@echo off
chcp 65001 >nul
echo ========================================
echo 快速测试 Streamlit
echo ========================================
echo.

cd /d "%~dp0"

echo [步骤1] 检查虚拟环境...
if not exist "venv\Scripts\activate.bat" (
    echo   ✗ 虚拟环境不存在
    echo.
    echo   正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo   [错误] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo   ✓ 虚拟环境已创建
) else (
    echo   ✓ 虚拟环境已存在
)
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

echo [步骤3] 检查并安装依赖...
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo   Streamlit 未安装，正在安装...
    python -m pip install --upgrade pip --quiet
    python -m pip install streamlit pandas openpyxl
    if errorlevel 1 (
        echo   [错误] 依赖安装失败
        pause
        exit /b 1
    )
    echo   ✓ 依赖已安装
) else (
    echo   ✓ Streamlit 已安装
)
echo.

echo [步骤4] 运行测试...
echo.
python test_streamlit_minimal.py
echo.

pause
