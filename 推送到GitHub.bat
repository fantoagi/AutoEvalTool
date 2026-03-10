@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo AutoEvalTool - 自动推送到 GitHub
echo ========================================

:: 1. 提交最新变更
echo.
echo [1/3] 提交变更...
git add .
git status
git commit -m "feat: 更新" 2>nul

:: 2. 尝试 gh 创建并推送
echo.
echo [2/3] 创建 GitHub 仓库并推送...
where gh >nul 2>&1
if errorlevel 1 goto :manual

:: 若设置了 GITHUB_TOKEN 或 GH_TOKEN 则自动登录（完全无需手动）
if defined GITHUB_TOKEN (
    echo !GITHUB_TOKEN! | gh auth login --with-token 2>nul
) else if defined GH_TOKEN (
    echo !GH_TOKEN! | gh auth login --with-token 2>nul
)

gh repo create AutoEvalTool --private --source=. --push 2>nul
if not errorlevel 1 (
    echo.
    echo [成功] 已推送到 GitHub
    goto :end
)

:: 未登录则打开浏览器登录（仅需一次）
gh auth status 2>nul
if not errorlevel 1 goto :try_push
echo 正在打开浏览器进行 GitHub 登录...
gh auth login --web --git-protocol https
gh repo create AutoEvalTool --private --source=. --push 2>nul
if not errorlevel 1 (
    echo.
    echo [成功] 已推送到 GitHub
    goto :end
)

:try_push
:: 仓库已存在时，添加 remote 并推送
for /f "tokens=*" %%u in ('gh repo view AutoEvalTool --json url -q ".url" 2^>nul') do set REPO_URL=%%u
if defined REPO_URL (
    git remote remove origin 2>nul
    git remote add origin !REPO_URL!
    git branch -M main 2>nul
    git push -u origin main 2>nul
    if not errorlevel 1 (
        echo.
        echo [成功] 已推送到 GitHub
        goto :end
    )
)

:: 3. 若已有 remote 则直接 push
echo.
echo [3/3] 推送到远程...
git remote -v | findstr origin >nul 2>&1
if not errorlevel 1 (
    git branch -M main 2>nul
    git push -u origin main
    if not errorlevel 1 (
        echo.
        echo [成功] 已推送到 GitHub
        goto :end
    )
)

:manual
echo.
echo [提示] 完全自动推送需设置 GITHUB_TOKEN 环境变量：
echo   1. 打开 https://github.com/settings/tokens 创建 token（勾选 repo 权限）
echo   2. 设置环境变量: setx GITHUB_TOKEN 你的token
echo   3. 重新打开终端，运行本脚本
echo.
echo 或手动登录（仅需一次）：
echo   gh auth login
echo   然后重新运行本脚本

:end
pause
