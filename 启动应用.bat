@echo off
chcp 65001 >nul
echo ========================================
echo 启动 Streamlit 应用
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

echo [步骤3] 检查应用文件...
if not exist "app.py" (
    echo   ✗ app.py 不存在
    pause
    exit /b 1
)
echo   ✓ app.py 存在
echo.

echo [步骤4] 启动 Streamlit 应用...
echo.
echo   应用将在浏览器中自动打开
echo   如果没有自动打开，请访问: http://localhost:8501
echo.
echo   按 Ctrl+C 停止应用
echo.

python -m streamlit run app.py --server.headless=false --server.port=8501

pause
