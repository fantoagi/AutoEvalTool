# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

# 获取当前工作目录（应该是 DemoV3 目录）
# 在 .spec 文件中，我们可以使用 os.getcwd() 或直接使用相对路径
current_dir = os.getcwd()

# 收集 streamlit 的所有数据
tmp_ret = collect_all('streamlit')
streamlit_datas = tmp_ret[0]
streamlit_binaries = tmp_ret[1]
streamlit_hiddenimports = tmp_ret[2]

# 数据文件：包含 config、app.py（确保 Streamlit 能找到它）
# 使用绝对路径确保文件被正确找到
app_py_path = os.path.join(current_dir, 'app.py')
config_dir = os.path.join(current_dir, 'config')

# 验证文件是否存在
if not os.path.exists(app_py_path):
    print(f"警告: app.py 不存在于 {app_py_path}")

# 仅包含存在的文件/目录（辅助小结 已移除，应用使用 UI 中的提示词模板）
datas = [(app_py_path, '.')]  # 将 app.py 复制到临时目录的根目录
if os.path.exists(config_dir):
    datas.insert(0, (config_dir, 'config'))
datas = datas + streamlit_datas

# 若存在 辅助小结 目录则加入（可选，当前应用使用 UI 提示词模板，无需此目录）
prompt_dir = os.path.join(current_dir, '辅助小结')
if os.path.exists(prompt_dir):
    datas.insert(1, (prompt_dir, '辅助小结'))

binaries = streamlit_binaries

hiddenimports = [
    'streamlit',
    'streamlit.web',
    'streamlit.web.cli',
    'streamlit.web.bootstrap',
    'streamlit.web.server',
    'streamlit.runtime',
    'streamlit.runtime.scriptrunner',
    'streamlit.runtime.state',
    'importlib.metadata',
    'importlib_metadata',
    'pkg_resources',
    'pandas',
    'openpyxl',
    'sqlite3',
    'configparser',
    'urllib',
    'urllib.request',
    'urllib.error',
    'urllib.parse',
    'hmac',
    'hashlib',
    'base64',
    'app',  # 明确包含 app 模块
    'llm_service',  # 包含所有自定义模块
    'utils',
    'database',
] + streamlit_hiddenimports

a = Analysis(
    ['run_gui.py'],
    pathex=[current_dir],  # 添加当前目录到搜索路径
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['langchain'],  # 排除 langchain，避免 streamlit.external.langchain 收集失败警告
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AutoEvalTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台，方便调试
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
