@echo off
chcp 65001 >nul
echo ========================================
echo 使用 Python 3.11 创建虚拟环境（推荐）
echo ========================================
echo.
echo 此脚本将使用 Python 3.11 创建新的虚拟环境
echo Python 3.11 有完整的预编译包支持，避免构建问题
echo.
pause

cd /d "%~dp0"

echo [步骤1] 检查 Python 3.11...
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ 未找到 Python 3.11
    echo.
    echo   请先安装 Python 3.11：
    echo   1. 访问 https://www.python.org/downloads/
    echo   2. 下载并安装 Python 3.11.x
    echo   3. 安装时勾选"Add Python to PATH"
    echo.
    pause
    exit /b 1
)
echo   ✓ Python 3.11 已找到
py -3.11 --version
echo.

echo [步骤2] 删除旧的虚拟环境（如果存在）...
if exist "venv" (
    echo   正在删除旧的虚拟环境...
    rmdir /s /q "venv" 2>nul
    timeout /t 1 /nobreak >nul
)
echo   ✓ 清理完成
echo.

echo [步骤3] 使用 Python 3.11 创建新的虚拟环境...
py -3.11 -m venv venv
if errorlevel 1 (
    echo   [错误] 虚拟环境创建失败
    pause
    exit /b 1
)
echo   ✓ 虚拟环境已创建
echo.

echo [步骤4] 激活虚拟环境...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo   [错误] 无法激活虚拟环境
    pause
    exit /b 1
)
echo   ✓ 虚拟环境已激活
echo.

echo [步骤5] 升级 pip...
python -m pip install --upgrade pip setuptools wheel --quiet
echo   ✓ pip 已升级
echo.

echo [步骤6] 安装依赖（使用预编译包）...
set PYTHONIOENCODING=utf-8
set PIP_USE_PEP517=false
pip install numpy pandas openpyxl --only-binary :all: --quiet
if errorlevel 1 (
    echo   [警告] 预编译包安装失败，尝试普通安装...
    pip install numpy pandas openpyxl --quiet
)
echo   ✓ 依赖已安装
echo.

echo [步骤7] 安装兼容旧浏览器的 Streamlit...
pip install "streamlit>=1.26.0,<1.27.0" --only-binary :all:
if errorlevel 1 (
    echo   [警告] 预编译包安装失败，尝试普通安装...
    pip install "streamlit>=1.26.0,<1.27.0"
)
echo   ✓ Streamlit 已安装
echo.

echo [步骤8] 验证安装...
python -c "import streamlit; print('Streamlit 版本:', streamlit.__version__)"
python -c "import numpy; print('NumPy 版本:', numpy.__version__)"
echo.

echo ========================================
echo 环境设置完成！
echo ========================================
echo.
echo 已使用 Python 3.11 创建虚拟环境
echo 已安装 Streamlit 1.26.x（兼容旧浏览器）
echo.
echo 下一步：
echo 1. 测试应用: python -m streamlit run app.py
echo 2. 如果正常，重新打包: .\打包应用.bat
echo.
pause
