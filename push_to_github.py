"""
自动初始化 Git 并推送到 GitHub
需要：已安装 Git，且已配置 GitHub 认证（SSH 或 HTTPS + 凭据）
"""
import os
import subprocess
import sys

REPO_NAME = "AutoEvalTool"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run(cmd, check=True):
    """执行命令"""
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.stdout:
        print(r.stdout)
    if r.stderr:
        print(r.stderr, file=sys.stderr)
    if check and r.returncode != 0:
        raise RuntimeError(f"命令失败: {' '.join(cmd)}")
    return r.returncode == 0


def main():
    print("=" * 50)
    print("AutoEvalTool - 自动推送到 GitHub")
    print("=" * 50)

    # 1. 检查 Git
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[错误] 未找到 Git，请先安装: https://git-scm.com/")
        return 1

    # 2. 初始化（若需要）
    if not os.path.exists(os.path.join(SCRIPT_DIR, ".git")):
        print("\n[1/4] 初始化 Git 仓库...")
        run(["git", "init"])
    else:
        print("\n[1/4] Git 仓库已存在")

    # 3. 添加并提交
    print("\n[2/4] 添加文件...")
    run(["git", "add", "."])
    run(["git", "status"])
    print("\n[3/4] 提交...")
    run(["git", "commit", "-m", "feat: LLM 自动化答案评估与对比工具"], check=False)
    # 若没有变更，commit 可能返回 1，可忽略

    # 4. 远程与推送
    print("\n[4/4] 配置远程并推送...")
    remote_url = os.environ.get("GITHUB_REPO_URL")
    if not remote_url:
        # 尝试从 gh 获取
        try:
            r = subprocess.run(
                ["gh", "repo", "create", REPO_NAME, "--private", "--source", ".", "--push"],
                cwd=SCRIPT_DIR, capture_output=True, text=True
            )
            if r.returncode == 0:
                print("[成功] 已创建仓库并推送")
                return 0
        except FileNotFoundError:
            pass

        print("\n[提示] 请先创建 GitHub 仓库，然后执行：")
        print("  git remote add origin https://github.com/你的用户名/仓库名.git")
        print("  git branch -M main")
        print("  git push -u origin main")
        print("\n或设置环境变量 GITHUB_REPO_URL 后重新运行此脚本")
        return 0

    run(["git", "remote", "remove", "origin"], check=False)
    run(["git", "remote", "add", "origin", remote_url])
    run(["git", "branch", "-M", "main"])
    run(["git", "push", "-u", "origin", "main"])
    print("\n[成功] 已推送到 GitHub")
    return 0


if __name__ == "__main__":
    sys.exit(main())
