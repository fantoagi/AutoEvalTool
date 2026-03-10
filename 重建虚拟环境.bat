@echo off
chcp 65001 >nul
echo ========================================
echo 重建虚拟环境
echo ========================================
echo.
echo 此脚本将删除旧的虚拟环境并创建新的
echo.

cd /d "%~dp0"

echo [步骤1] 删除旧的虚拟环境...
if exist "venv" (
    echo   正在删除 venv 文件夹...
    rmdir /s /q "venv" 2>nul
    if errorlevel 1 (
        echo   [警告] 无法删除，可能正在被使用
        echo   请关闭所有使用虚拟环境的程序后重试
        pause
        exit /b 1
    )
    echo   [成功] 旧虚拟环境已删除
    timeout /t 1 /nobreak >nul
) else (
    echo   [提示] 虚拟环境不存在，跳过删除
)
echo.

echo [步骤2] 创建新的虚拟环境...
python -m venv venv
if errorlevel 1 (
    echo   [错误] 虚拟环境创建失败
    pause
    exit /b 1
)
echo   [成功] 虚拟环境已创建
echo.

echo [步骤3] 验证虚拟环境...
if not exist "venv\Scripts\activate.bat" (
    echo   [错误] activate.bat 不存在，虚拟环境创建不完整
    pause
    exit /b 1
)
if not exist "venv\Scripts\python.exe" (
    echo   [错误] python.exe 不存在，虚拟环境创建不完整
    pause
    exit /b 1
)
echo   [成功] 虚拟环境验证通过
echo.

echo [步骤4] 激活虚拟环境并安装依赖...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo   [错误] 无法激活虚拟环境
    pause
    exit /b 1
)
echo   [成功] 虚拟环境已激活
echo.

echo [步骤5] 升级 pip...
python -m pip install --upgrade pip --quiet
echo   [完成] pip 已升级
echo.

echo [步骤6] 安装依赖...
python -m pip install streamlit pandas openpyxl
if errorlevel 1 (
    echo   [错误] 依赖安装失败
    pause
    exit /b 1
)
echo   [成功] 依赖已安装
echo.

echo [步骤7] 测试 Streamlit...
python test_streamlit_safe.py
if errorlevel 1 (
    echo.
    echo   [警告] Streamlit 测试失败，但环境已设置完成
    echo   可以尝试手动运行: python -m streamlit run app.py
) else (
    echo   [成功] Streamlit 测试通过
)
echo.

echo ========================================
echo 虚拟环境重建完成！
echo ========================================
echo.
echo 现在可以运行应用：
echo   venv\Scripts\activate
echo   python -m streamlit run app.py --server.headless=true
echo.
pause
