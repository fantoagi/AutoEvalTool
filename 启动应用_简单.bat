@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 正在启动应用...
echo.

call "venv\Scripts\activate.bat" 2>nul

REM 检查端口
netstat -ano | findstr ":8501" >nul
if not errorlevel 1 (
    set PORT=8502
    echo 端口 8501 被占用，使用端口 8502
) else (
    set PORT=8501
)

REM 启动 Streamlit
echo 启动 Streamlit（端口 %PORT%）...
start /B python -m streamlit run app.py --server.port=%PORT% --server.headless=false

REM 等待启动
timeout /t 3 /nobreak >nul

REM 打开浏览器
start http://localhost:%PORT%

echo.
echo 应用地址：http://localhost:%PORT%
echo 如果浏览器未自动打开，请手动访问上述地址
echo.
echo 按任意键退出...
pause >nul
