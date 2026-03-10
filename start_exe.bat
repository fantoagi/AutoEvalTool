@echo off
chcp 65001 >nul
echo ========================================
echo LLM 自动化答案评估工具 - 启动（打包版）
echo ========================================
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查可执行文件是否存在
if not exist "dist\AutoEvalTool.exe" (
    echo [错误] 未找到可执行文件: dist\AutoEvalTool.exe
    echo.
    echo 请先运行打包脚本:
    echo   python build.py
    echo.
    pause
    exit /b 1
)

echo [启动] 正在启动 AutoEvalTool.exe...
echo 应用将在 8 秒后自动打开浏览器: http://127.0.0.1:8501
echo.
echo ========================================
echo.

REM 启动可执行文件
start "" "dist\AutoEvalTool.exe"

echo [提示] 程序已在后台启动
echo 如果浏览器没有自动打开，请手动访问: http://127.0.0.1:8501
echo.
pause
