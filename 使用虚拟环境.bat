@echo off
chcp 65001 >nul
echo ========================================
echo 使用虚拟环境运行（推荐）
echo ========================================
echo.
echo 这将创建一个全新的 Python 环境，避免现有环境的问题
echo.

cd /d "%~dp0"

echo [步骤1] 检查并创建虚拟环境...
if exist "venv\Scripts\activate.bat" (
    echo   虚拟环境已存在且完整，跳过创建
) else (
    if exist "venv" (
        echo   发现不完整的虚拟环境，正在删除...
        rmdir /s /q "venv" 2>nul
    )
    echo   正在创建新的虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo   [错误] 虚拟环境创建失败
        pause
        exit /b 1
    )
    if not exist "venv\Scripts\activate.bat" (
        echo   [错误] 虚拟环境创建不完整，activate.bat 不存在
        pause
        exit /b 1
    )
    echo   [成功] 虚拟环境已创建
)
echo.

echo [步骤2] 激活虚拟环境...
if not exist "venv\Scripts\activate.bat" (
    echo   [错误] activate.bat 文件不存在，虚拟环境可能损坏
    echo   请删除 venv 文件夹后重试
    pause
    exit /b 1
)
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo   [错误] 无法激活虚拟环境
    echo   尝试使用完整路径...
    call "%~dp0venv\Scripts\activate.bat"
    if errorlevel 1 (
        echo   [错误] 激活仍然失败，请手动检查虚拟环境
        pause
        exit /b 1
    )
)
echo   [成功] 虚拟环境已激活
echo.

echo [步骤3] 升级 pip...
python -m pip install --upgrade pip --quiet
echo.

echo [步骤4] 安装依赖...
python -m pip install streamlit pandas openpyxl --quiet
if errorlevel 1 (
    echo   [错误] 依赖安装失败
    pause
    exit /b 1
)
echo   [成功] 依赖已安装
echo.

echo [步骤5] 测试 Streamlit...
python test_streamlit_safe.py
if errorlevel 1 (
    echo.
    echo   [错误] Streamlit 测试失败
    pause
    exit /b 1
)
echo.

echo ========================================
echo 虚拟环境设置完成！
echo ========================================
echo.
echo 现在可以运行应用：
echo   python -m streamlit run app.py --server.headless=true
echo.
echo 注意：每次使用前需要激活虚拟环境：
echo   venv\Scripts\activate
echo.
pause
