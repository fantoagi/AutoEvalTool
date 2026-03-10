@echo off
chcp 65001 >nul
echo ========================================
echo 完全重置 Streamlit 环境
echo ========================================
echo.
echo 此脚本将：
echo 1. 结束所有 Python 进程
echo 2. 删除 Streamlit 配置
echo 3. 重新安装 Streamlit
echo.
echo 警告：这将删除 Streamlit 的所有配置！
echo.
pause

echo.
echo [步骤1] 结束所有 Python 进程...
taskkill /F /IM python.exe 2>nul
if errorlevel 1 (
    echo   没有找到运行中的 Python 进程
) else (
    echo   Python 进程已结束
)
timeout /t 2 /nobreak >nul
echo.

echo [步骤2] 删除 Streamlit 配置...
set STREAMLIT_DIR=%USERPROFILE%\.streamlit
if exist "%STREAMLIT_DIR%" (
    rmdir /s /q "%STREAMLIT_DIR%" 2>nul
    if errorlevel 1 (
        echo   [警告] 无法删除，可能正在被使用
    ) else (
        echo   [成功] Streamlit 配置已删除
    )
) else (
    echo   [提示] 配置目录不存在
)
echo.

echo [步骤3] 重新安装 Streamlit（不使用缓存）...
python -m pip uninstall streamlit -y
python -m pip install streamlit --no-cache-dir
if errorlevel 1 (
    echo   [错误] Streamlit 安装失败
    pause
    exit /b 1
) else (
    echo   [成功] Streamlit 已重新安装
)
echo.

echo ========================================
echo 重置完成！
echo ========================================
echo.
echo 现在可以尝试运行：
echo   python test_streamlit_safe.py
echo.
pause
