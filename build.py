"""
Auto-Eval Agent - Windows 打包脚本 (Python 版本)
避免批处理文件的编码问题
"""
import os
import sys
import subprocess
import shutil

def main():
    print("=" * 60)
    print("Auto-Eval Agent - Windows 打包脚本")
    print("=" * 60)
    print()
    
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"工作目录: {script_dir}")
    print(f"Python 可执行文件: {sys.executable}")
    print()
    
    # [1/4] 检查 Python
    print("[1/4] 确认 Python 和 pip 可用...")
    try:
        result = subprocess.run([sys.executable, "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"[成功] {result.stdout.strip()}")
    except Exception as e:
        print(f"[错误] 无法运行 Python: {e}")
        input("按 Enter 键退出...")
        return 1
    print()
    
    # [2/4] 检查依赖（如果使用虚拟环境，依赖应该已经安装）
    print("[2/4] 检查依赖包...")
    
    # 检查关键依赖是否已安装
    required_packages = ['streamlit', 'pandas', 'openpyxl']
    missing_packages = []
    
    for package in required_packages:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"  ✓ {package} 已安装")
            else:
                missing_packages.append(package)
                print(f"  ✗ {package} 未安装")
        except Exception as e:
            print(f"  ⚠ 检查 {package} 时出错: {e}")
            missing_packages.append(package)
    
    # 如果缺少依赖，尝试安装
    if missing_packages:
        print(f"\n检测到缺少依赖: {', '.join(missing_packages)}")
        print("正在安装 requirements.txt 中的依赖...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                timeout=600,  # 10分钟超时
                check=True
            )
            print("[成功] 依赖已安装")
        except subprocess.TimeoutExpired:
            print("[错误] 依赖安装超时，请检查网络连接")
            input("按 Enter 键退出...")
            return 1
        except Exception as e:
            print(f"[错误] 依赖安装失败: {e}")
            print("[提示] 可以尝试手动运行: pip install -r requirements.txt")
            input("按 Enter 键退出...")
            return 1
    else:
        print("[提示] 所有依赖已安装，跳过安装步骤")
    print()
    
    # 检查 PyInstaller
    print("检查 PyInstaller...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "pyinstaller"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("[提示] PyInstaller 已安装")
        else:
            print("正在安装 PyInstaller...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pyinstaller"],
                timeout=300,  # 5分钟超时
                check=True
            )
            print("[成功] PyInstaller 已安装")
    except subprocess.TimeoutExpired:
        print("[错误] PyInstaller 安装超时")
        input("按 Enter 键退出...")
        return 1
    except Exception as e:
        print(f"[错误] PyInstaller 安装失败: {e}")
        input("按 Enter 键退出...")
        return 1
    print()
    
    # [3/4] 清理
    print("[3/4] 清理上一次构建结果...")
    for dir_name in ["build", "dist"]:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已清理 {dir_name} 目录")
    
    # 注意：不删除 AutoEvalTool.spec，保留用户的自定义配置
    print()
    
    # [4/4] 打包
    print("[4/4] 使用 PyInstaller 打包（这可能需要几分钟）...")
    print()
    
    # 使用 .spec 文件（如果存在）
    if os.path.exists("AutoEvalTool.spec"):
        print("使用 AutoEvalTool.spec 配置文件...")
        # 使用 .spec 文件时，不需要再添加 --collect-all，因为 .spec 文件中已经处理了
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "AutoEvalTool.spec"
        ]
    else:
        print("使用命令行参数打包...")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--onefile",
            "--name", "AutoEvalTool",
            "--collect-all", "streamlit",  # 收集 streamlit 的所有数据文件（包括元数据）
            "--add-data", "config;config",
            "--hidden-import", "streamlit",
            "--hidden-import", "importlib.metadata",
            "--hidden-import", "importlib_metadata",
            "--hidden-import", "pkg_resources",
            "--hidden-import", "pandas",
            "--hidden-import", "openpyxl",
            "--hidden-import", "sqlite3",
            "--hidden-import", "configparser",
            "--hidden-import", "urllib",
            "--hidden-import", "hmac",
            "--hidden-import", "hashlib",
            "--hidden-import", "base64",
            "run_gui.py"
        ]
    
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"[错误] PyInstaller 打包失败: {e}")
        input("按 Enter 键退出...")
        return 1
    
    # 验证打包结果：检查 app.py 是否被包含
    print()
    print("验证打包结果...")
    analysis_toc = os.path.join(script_dir, "build", "AutoEvalTool", "Analysis-00.toc")
    if os.path.exists(analysis_toc):
        with open(analysis_toc, 'r', encoding='utf-8') as f:
            toc_content = f.read()
            if 'app.py' in toc_content:
                print("[成功] app.py 已被包含到打包文件中")
            else:
                print("[警告] app.py 可能未被包含，请检查 .spec 文件")
    
    # 显示结果
    exe_path = os.path.join(script_dir, "dist", "AutoEvalTool.exe")
    print()
    print("=" * 60)
    print("[成功] 打包完成！")
    print("=" * 60)
    print("可执行文件位置:")
    print(f'  "{exe_path}"')
    print()
    
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path)
        size_mb = size / (1024 * 1024)
        print(f"文件大小: {size_mb:.2f} MB")
    print()
    print("提示：将此 exe 文件复制到任何 Windows 电脑上即可运行")
    print("=" * 60)
    print()
    input("按 Enter 键退出...")
    return 0

if __name__ == "__main__":
    sys.exit(main())
