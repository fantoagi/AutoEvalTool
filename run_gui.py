"""
Windows 启动入口脚本
用于打包为可执行文件后启动 Streamlit 应用。
"""
import os
import sys
import time
import webbrowser
import threading
import subprocess

# PyInstaller 打包后的路径处理
if getattr(sys, 'frozen', False):
    # 打包后的环境：使用临时解压目录
    base_dir = sys._MEIPASS
    # 将临时目录添加到 sys.path，确保能找到所有模块
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
else:
    # 开发环境：使用脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

# 直接导入 app 模块，确保 PyInstaller 包含它
try:
    import app
except ImportError as e:
    print(f"错误：无法导入 app 模块: {e}")
    print(f"当前 sys.path: {sys.path}")
    input("按 Enter 键退出...")
    sys.exit(1)

# 导入 Streamlit 相关模块
# 注意：在 PyInstaller 环境中，需要确保 Streamlit 正确导入
try:
    import streamlit
    import streamlit.web.bootstrap
    import streamlit.web.cli as stcli
except ImportError as e:
    print(f"错误：无法导入 Streamlit 模块: {e}")
    print(f"当前 sys.path: {sys.path}")
    input("按 Enter 键退出...")
    sys.exit(1)


def main() -> None:
    # 方法1：优先使用 app.__file__（如果存在且文件存在）
    app_path = None
    if hasattr(app, '__file__'):
        app_path = app.__file__
        print(f"方法1: 使用 app.__file__ = {app_path}")
        if os.path.exists(app_path):
            print(f"[成功] 找到 app.py 文件: {app_path}")
        else:
            print(f"[失败] app.__file__ 指向的文件不存在")
            app_path = None
    
    # 方法2：如果方法1失败，尝试在 base_dir 根目录查找
    if not app_path or not os.path.exists(app_path):
        app_path = os.path.join(base_dir, "app.py")
        print(f"方法2: 尝试 base_dir/app.py = {app_path}")
        if os.path.exists(app_path):
            print(f"[成功] 找到 app.py 文件: {app_path}")
        else:
            print(f"[失败] base_dir/app.py 不存在")
            app_path = None
    
    # 方法3：如果还是找不到，列出 base_dir 中的所有文件，帮助调试
    if not app_path or not os.path.exists(app_path):
        print(f"\n[调试] 无法找到 app.py，列出 base_dir 中的所有文件:")
        print(f"base_dir = {base_dir}")
        try:
            all_items = os.listdir(base_dir)
            py_files = [item for item in all_items if item.endswith('.py')]
            dirs = [item for item in all_items if os.path.isdir(os.path.join(base_dir, item))]
            
            if py_files:
                print(f"  Python 文件: {', '.join(py_files)}")
            else:
                print(f"  (没有找到 .py 文件)")
            
            if dirs:
                print(f"  目录: {', '.join(dirs[:10])}")  # 只显示前10个目录
            
            # 尝试在所有 .py 文件中查找
            for py_file in py_files:
                full_path = os.path.join(base_dir, py_file)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline()
                        if 'streamlit' in first_line.lower() or 'st.title' in f.read(1000):
                            print(f"  [提示] 发现可能的 Streamlit 文件: {py_file}")
                            app_path = full_path
                            break
                except:
                    pass
        except Exception as e:
            print(f"  无法列出目录: {e}")
    
    # 最终验证
    if not app_path or not os.path.exists(app_path):
        print(f"\n[错误] 无法找到 app.py 文件")
        print(f"尝试的路径: {app_path}")
        print(f"base_dir: {base_dir}")
        print(f"app 模块位置: {app.__file__ if hasattr(app, '__file__') else 'N/A'}")
        input("按 Enter 键退出...")
        sys.exit(1)
    
    # 确保 app_path 是绝对路径（保持 Windows 路径格式）
    app_path = os.path.abspath(app_path)
    print(f"[验证] 应用文件路径: {app_path}")
    print(f"[验证] 文件大小: {os.path.getsize(app_path)} 字节")
    print(f"[验证] 路径格式: {'绝对路径' if os.path.isabs(app_path) else '相对路径'}")
    
    print(f"\n正在启动 Streamlit 应用...")
    print(f"应用文件: {app_path}")
    
    # 创建 Streamlit 配置文件（临时），禁用 Node dev server
    # 在 PyInstaller 环境中，Node.js 可能不可用，导致 dev server 无法启动
    # 注意：Streamlit 会查找用户目录下的 .streamlit/config.toml
    # 但在打包环境中，我们也需要在临时目录创建一份
    
    # 方法1：在用户目录创建（Streamlit 默认查找的位置）
    user_home = os.path.expanduser('~')
    user_config_dir = os.path.join(user_home, '.streamlit')
    if not os.path.exists(user_config_dir):
        os.makedirs(user_config_dir, exist_ok=True)
    
    user_config_file = os.path.join(user_config_dir, 'config.toml')
    
    # 方法2：在临时目录也创建一份（备用）
    temp_config_dir = os.path.join(base_dir, '.streamlit')
    if not os.path.exists(temp_config_dir):
        os.makedirs(temp_config_dir, exist_ok=True)
    
    temp_config_file = os.path.join(temp_config_dir, 'config.toml')
    
    config_content = """[global]
developmentMode = false

[server]
port = 8501
address = "127.0.0.1"
headless = true
enableCORS = true
enableXsrfProtection = false
runOnSave = false
enableStaticServing = true

[browser]
gatherUsageStats = false
serverAddress = "127.0.0.1"
serverPort = 8501

[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
"""
    # 在两个位置都创建配置文件
    for config_file in [user_config_file, temp_config_file]:
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            print(f"[配置] 已创建配置文件: {config_file}")
        except Exception as e:
            print(f"[警告] 无法创建配置文件 {config_file}: {e}")
    
    # 设置环境变量，告诉 Streamlit 配置文件的位置
    os.environ['STREAMLIT_CONFIG_FILE'] = user_config_file
    
    # 设置环境变量，使用 IPv4 地址（127.0.0.1）而不是 localhost，避免 IPv6 问题
    # 关键：禁用开发模式，允许使用 server.port
    os.environ['STREAMLIT_GLOBAL_DEVELOPMENT_MODE'] = 'false'
    os.environ['STREAMLIT_SERVER_PORT'] = '8501'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '127.0.0.1'  # 使用 IPv4，避免 IPv6 (::1) 问题
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    # 关键：禁用 Node dev server，强制使用主服务器
    os.environ['STREAMLIT_SERVER_ENABLE_STATIC_SERVING'] = 'true'
    os.environ['STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION'] = 'false'
    # 禁用自动打开浏览器（避免打开错误的端口）
    os.environ['STREAMLIT_BROWSER_SERVER_ADDRESS'] = '127.0.0.1'
    os.environ['STREAMLIT_BROWSER_SERVER_PORT'] = '8501'
    
    # 命令行参数：现在开发模式已禁用，可以安全地使用 server.port
    # 注意：app_path 已经作为第一个参数传入 bootstrap.run，所以 args 中不需要再包含它
    args = [
        '--server.port=8501',  # 现在可以安全使用，因为开发模式已禁用
        '--server.address=127.0.0.1',  # 使用 IPv4，避免 IPv6 问题
        '--server.headless=true',
        '--browser.gatherUsageStats=false',
        '--server.enableCORS=true',
        '--server.enableXsrfProtection=false',
    ]
    
    print(f"Streamlit 端口: 8501")
    print(f"=" * 60)
    print(f"重要提示：")
    print(f"1. Streamlit 主服务器将在 8501 端口启动（使用 127.0.0.1）")
    print(f"2. 如果看到 'Local URL: http://localhost:3000'，请忽略它（那是 Node dev server，不可用）")
    print(f"3. 程序将在 8 秒后自动打开: http://127.0.0.1:8501")
    print(f"4. 如果无法访问，请尝试: http://localhost:8501")
    print(f"5. 如果 8501 被占用，请查看下方日志中的 'Server started on port XXXX'，访问该端口")
    print(f"6. 不要访问 3000 端口，它无法连接")
    print(f"7. ⚠️  浏览器要求：Chrome/Edge 93+, Firefox 92+, Safari 15.4+")
    print(f"   如果看到 'Object.hasOwn is not a function' 错误，请升级浏览器")
    print(f"=" * 60)
    print()
    
    # 禁用 Streamlit 的自动打开浏览器（避免打开错误的 3000 端口）
    os.environ['STREAMLIT_BROWSER_SERVER_ADDRESS'] = 'localhost'
    os.environ['STREAMLIT_BROWSER_SERVER_PORT'] = '8501'
    
    # 在后台线程中等待服务器启动，然后打开正确的端口
    def open_browser_after_delay():
        """等待服务器启动后，打开正确的端口"""
        time.sleep(8)  # 等待 8 秒让服务器完全启动
        # 使用 127.0.0.1 而不是 localhost，避免 IPv6 问题
        url = 'http://127.0.0.1:8501'
        try:
            webbrowser.open(url)
            print(f"\n[自动打开] 已在浏览器中打开: {url}")
            print(f"如果无法访问，请尝试: http://localhost:8501")
        except Exception as e:
            print(f"\n[警告] 无法自动打开浏览器: {e}")
            print(f"请手动在浏览器中访问: {url}")
            print(f"或尝试: http://localhost:8501")
    
    # 启动后台线程
    browser_thread = threading.Thread(target=open_browser_after_delay, daemon=True)
    browser_thread.start()
    
    try:
        # 方法1：尝试使用 streamlit.web.bootstrap.run
        # 如果失败，会回退到方法2（subprocess）
        print(f"[调试] 启动参数:")
        print(f"  应用文件: {app_path}")
        print(f"  文件是否存在: {os.path.exists(app_path)}")
        print(f"  命令行参数: {args}")
        print()
        
        # 验证文件内容（确保是有效的 Streamlit 应用）
        try:
            with open(app_path, 'r', encoding='utf-8') as f:
                content = f.read(500)  # 读取前500个字符
                if 'streamlit' not in content.lower() and 'st.' not in content:
                    print(f"[警告] app.py 文件可能不是有效的 Streamlit 应用")
                else:
                    print(f"[验证] app.py 文件包含 Streamlit 代码")
        except Exception as e:
            print(f"[警告] 无法读取 app.py 文件: {e}")
        
        print(f"\n[启动] 正在启动 Streamlit 服务器...")
        print(f"[启动] 应用文件: {app_path}")
        print()
        
        # 方法1：使用 streamlit.web.cli.main（最可靠的方式）
        # 这是 Streamlit 官方推荐的启动方式
        try:
            print(f"[方法1] 使用 streamlit.web.cli.main 启动...")
            
            # 构建完整的命令行参数，模拟: streamlit run app.py --server.port=8501 ...
            cli_args = ['streamlit', 'run', app_path] + args
            
            print(f"[方法1] 命令行参数: {cli_args}")
            
            # 保存原始 argv
            original_argv = sys.argv.copy()
            try:
                # 设置 sys.argv 为 Streamlit CLI 期望的格式
                sys.argv = cli_args
                
                # 调用 Streamlit CLI 的 main 函数
                # 这会解析参数并启动服务器
                stcli.main()
            finally:
                # 恢复原始 argv
                sys.argv = original_argv
                
        except SystemExit as e:
            # SystemExit 是正常的（Streamlit 正常退出时会抛出）
            if e.code == 0:
                print("[正常退出] Streamlit 服务器已关闭")
            else:
                raise
        except Exception as cli_error:
            print(f"[错误] CLI 方式启动失败: {cli_error}")
            import traceback
            traceback.print_exc()
            
            # 方法2：回退到 bootstrap.run
            print(f"\n[方法2] 尝试使用 bootstrap.run...")
            try:
                # 重新导入，确保模块状态正确
                import importlib
                import streamlit.web.bootstrap as bootstrap_module
                importlib.reload(bootstrap_module)
                
                # 使用 bootstrap.run
                bootstrap_module.run(
                    app_path,
                    "streamlit",
                    args,
                    {}
                )
            except Exception as bootstrap_error:
                print(f"[错误] bootstrap.run 也失败: {bootstrap_error}")
                import traceback
                traceback.print_exc()
                raise
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"错误：启动 Streamlit 失败: {e}")
        import traceback
        traceback.print_exc()
        input("按 Enter 键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
