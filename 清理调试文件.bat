@echo off
chcp 65001 >nul
echo ========================================
echo 清理调试和测试文件
echo ========================================
echo.
echo 此脚本将删除以下类型的文件：
echo 1. 测试文件（test_*.py）
echo 2. 诊断文件（diagnose*.py, check_port.*）
echo 3. 调试脚本（start_debug.bat 等）
echo 4. 临时文件（__pycache__, .DS_Store）
echo 5. 重复的文档（保留经验总结）
echo.
pause

cd /d "%~dp0"

echo [步骤1] 删除测试文件...
del /q test_*.py 2>nul
if errorlevel 1 (
    echo   没有找到测试文件
) else (
    echo   ✓ 测试文件已删除
)
echo.

echo [步骤2] 删除诊断文件...
del /q diagnose*.py 2>nul
del /q check_port.* 2>nul
if errorlevel 1 (
    echo   没有找到诊断文件
) else (
    echo   ✓ 诊断文件已删除
)
echo.

echo [步骤3] 删除调试脚本...
del /q start_debug.bat 2>nul
del /q 运行测试.bat 2>nul
del /q 快速检查.bat 2>nul
del /q 强制诊断.bat 2>nul
if errorlevel 1 (
    echo   没有找到调试脚本
) else (
    echo   ✓ 调试脚本已删除
)
echo.

echo [步骤4] 删除重复的文档（保留经验总结）...
del /q 启动问题排查.md 2>nul
del /q 紧急修复指南.md 2>nul
del /q 终极解决方案.md 2>nul
del /q 问题排查步骤.md 2>nul
if errorlevel 1 (
    echo   没有找到重复文档
) else (
    echo   ✓ 重复文档已删除（已保留打包经验总结）
)
echo.

echo [步骤5] 清理 Python 缓存...
if exist "__pycache__" (
    rmdir /s /q "__pycache__" 2>nul
    echo   ✓ Python 缓存已删除
) else (
    echo   Python 缓存不存在
)
echo.

echo [步骤6] 删除 macOS 系统文件...
del /q .DS_Store 2>nul
del /q org\.DS_Store 2>nul
if errorlevel 1 (
    echo   没有找到 .DS_Store 文件
) else (
    echo   ✓ .DS_Store 文件已删除
)
echo.

echo [步骤7] 清理旧的构建脚本（保留主要脚本）...
del /q build_quick.bat 2>nul
del /q build_quick.py 2>nul
del /q build_windows.ps1 2>nul
if exist "build_windows.bat" (
    echo   保留 build_windows.bat（可能仍在使用）
)
echo   ✓ 旧的构建脚本已清理
echo.

echo ========================================
echo 清理完成！
echo ========================================
echo.
echo 已保留的重要文件：
echo   - 核心代码文件（app.py, run_gui.py 等）
echo   - 打包脚本（build.py, 打包应用.bat）
echo   - 启动脚本（启动应用.bat）
echo   - 经验文档（打包经验总结.md, 打包快速参考.md）
echo   - 配置目录（config/）
echo.
echo 已删除的文件类型：
echo   - 测试文件（test_*.py）
echo   - 诊断文件（diagnose*.py）
echo   - 调试脚本（start_debug.bat 等）
echo   - 重复文档（已合并到经验总结）
echo   - 临时文件（__pycache__, .DS_Store）
echo.
pause
