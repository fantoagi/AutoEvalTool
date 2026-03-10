@echo off
chcp 65001 >nul
echo ========================================
echo 修复 Streamlit 配置问题
echo ========================================
echo.
echo 此脚本将：
echo 1. 删除可能损坏的 Streamlit 配置
echo 2. 清理 Streamlit 缓存
echo.

set STREAMLIT_DIR=%USERPROFILE%\.streamlit
set STREAMLIT_CACHE=%USERPROFILE%\.streamlit\cache

echo [步骤1] 检查 Streamlit 配置目录...
if exist "%STREAMLIT_DIR%" (
    echo   找到配置目录: %STREAMLIT_DIR%
    echo   正在删除...
    rmdir /s /q "%STREAMLIT_DIR%" 2>nul
    if errorlevel 1 (
        echo   [警告] 无法删除，可能正在被使用
        echo   请手动关闭所有 Python/Streamlit 进程后重试
    ) else (
        echo   [成功] 配置目录已删除
    )
) else (
    echo   [提示] 配置目录不存在，跳过
)
echo.

echo [步骤2] 检查 Streamlit 缓存...
if exist "%STREAMLIT_CACHE%" (
    echo   找到缓存目录: %STREAMLIT_CACHE%
    echo   正在删除...
    rmdir /s /q "%STREAMLIT_CACHE%" 2>nul
    if errorlevel 1 (
        echo   [警告] 无法删除缓存
    ) else (
        echo   [成功] 缓存已删除
    )
) else (
    echo   [提示] 缓存目录不存在，跳过
)
echo.

echo ========================================
echo 修复完成！
echo ========================================
echo.
echo 现在可以尝试重新运行应用：
echo   python -m streamlit run app.py --server.headless=true
echo.
pause
