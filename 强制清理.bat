@echo off
chcp 65001 >nul
echo ========================================
echo 强制清理 - 解决 Streamlit 卡住问题
echo ========================================
echo.
echo 警告：此操作将：
echo 1. 强制结束所有 Python 进程
echo 2. 删除 Streamlit 配置
echo 3. 清理 Streamlit 缓存
echo.
pause

echo.
echo [步骤1] 强制结束所有 Python 进程...
taskkill /F /IM python.exe 2>nul
if errorlevel 1 (
    echo   [提示] 没有发现运行中的 Python 进程
) else (
    echo   [完成] 已结束所有 Python 进程
)
timeout /t 2 /nobreak >nul
echo.

echo [步骤2] 删除 Streamlit 配置目录...
set STREAMLIT_DIR=%USERPROFILE%\.streamlit
if exist "%STREAMLIT_DIR%" (
    echo   正在删除: %STREAMLIT_DIR%
    rmdir /s /q "%STREAMLIT_DIR%" 2>nul
    if errorlevel 1 (
        echo   [警告] 无法删除，可能正在被使用
        echo   请稍后手动删除: %STREAMLIT_DIR%
    ) else (
        echo   [成功] Streamlit 配置已删除
    )
) else (
    echo   [提示] Streamlit 配置目录不存在
)
echo.

echo [步骤3] 清理 Python 缓存...
if exist "__pycache__" (
    echo   正在删除 __pycache__...
    rmdir /s /q "__pycache__" 2>nul
)
if exist "*.pyc" (
    echo   正在删除 .pyc 文件...
    del /q "*.pyc" 2>nul
)
echo   [完成] 缓存已清理
echo.

echo [步骤4] 检查并清理虚拟环境缓存...
if exist "venv" (
    if exist "venv\__pycache__" (
        echo   正在清理虚拟环境缓存...
        rmdir /s /q "venv\__pycache__" 2>nul
    )
    if exist "venv\Lib\site-packages\streamlit\__pycache__" (
        echo   正在清理 Streamlit 缓存...
        rmdir /s /q "venv\Lib\site-packages\streamlit\__pycache__" 2>nul
    )
)
echo   [完成] 虚拟环境缓存已清理
echo.

echo ========================================
echo 清理完成！
echo ========================================
echo.
echo 建议下一步：
echo 1. 重启计算机（推荐）
echo 2. 或者运行"重建虚拟环境.bat"
echo 3. 然后运行"test_streamlit_safe.py"
echo.
pause
