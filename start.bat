@echo off
chcp 65001 >nul
echo ========================================
echo LLM 自动化答案评估工具 - 启动脚本
echo ========================================
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

echo 当前目录: %CD%
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

echo [1/3] 检查 Python 环境...
python --version
echo.

echo [2/3] 启动 Streamlit 应用...
echo 应用将在浏览器中自动打开: http://localhost:8501
echo 按 Ctrl+C 可以停止服务器
echo.
echo ========================================
echo.

REM 尝试使用 streamlit 命令（无浏览器模式，避免卡住）
echo [提示] 使用无浏览器模式启动，避免自动打开浏览器导致卡住
streamlit run app.py --server.headless=true --server.port=8501 2>nul
if errorlevel 1 (
    echo [提示] streamlit 命令不可用，使用 Python 模块方式...
    python -m streamlit run app.py --server.headless=true --server.port=8501
)

pause
