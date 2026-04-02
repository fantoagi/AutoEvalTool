"""
LLM 自动化答案评估与对比工具 (Auto-Eval Agent)
Streamlit主应用
"""
import streamlit as st
import pandas as pd
import io
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import Dict, Tuple
import json
import os
import sys
import configparser

from llm_service import call_llm
from utils import parse_llm_evaluation_response, calculate_accuracy
from database import init_database, save_eval_history, get_eval_history


# 页面配置
st.set_page_config(
    page_title="LLM 自动化答案评估工具",
    page_icon="🤖",
    layout="wide"
)

# 浏览器兼容性 Polyfill：为旧版浏览器添加 Object.hasOwn 支持
# 注意：Streamlit 的 JavaScript 在页面头部加载，我们需要尽可能早地注入 polyfill
# 使用 st.markdown 在页面最顶部注入，并确保立即执行（IIFE）
try:
    # 在页面最顶部注入 polyfill（立即执行函数，确保在 Streamlit JS 之前定义）
    # 使用 <script> 标签在页面头部注入，通过 markdown 渲染
    polyfill_html = """
    <script>
    // Object.hasOwn polyfill - 必须在 Streamlit JS 加载之前执行
    (function() {
        'use strict';
        // 如果已经支持，直接返回
        if (typeof Object.hasOwn === 'function') {
            return;
        }
        // Polyfill 实现（ES2022 Object.hasOwn 的兼容实现）
        Object.hasOwn = function hasOwn(obj, prop) {
            if (obj == null) {
                throw new TypeError('Cannot convert undefined or null to object');
            }
            return Object.prototype.hasOwnProperty.call(Object(obj), prop);
        };
        // 标记已加载
        if (typeof console !== 'undefined' && console.log) {
            console.log('[Polyfill] Object.hasOwn polyfill loaded for browser compatibility');
        }
    })();
    </script>
    """
    # 在页面最顶部注入（使用 markdown，会在 Streamlit 渲染时执行）
    # 注意：这会在页面加载时执行，但 Streamlit 的 JS 可能已经加载
    # 更好的方案是降级 Streamlit 版本（见 requirements.txt）
    st.markdown(polyfill_html, unsafe_allow_html=True)
except Exception as e:
    # 如果注入失败，不影响主功能
    import warnings
    warnings.warn(f"无法注入浏览器兼容性 polyfill: {e}，建议降级 Streamlit 版本")

# 延迟初始化数据库（避免导入时卡住）
# 数据库将在第一次使用时初始化
_db_initialized = False

def ensure_database():
    """确保数据库已初始化（延迟初始化）"""
    global _db_initialized
    if not _db_initialized:
        init_database()
        _db_initialized = True

# 配置文件路径（复用现有 summary_generation.cfg 中的比较模型配置）
# 兼容 PyInstaller 打包后的环境
if getattr(sys, 'frozen', False):
    # 打包后的环境：使用 exe 所在目录（用户可修改配置）
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    # 开发环境：使用脚本所在目录
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config", "summary_generation.cfg")
# 比较评估用提示词持久化文件（Markdown，换上传文件时仍保留上次编辑内容）
COMPARE_PROMPT_FILE = os.path.join(SCRIPT_DIR, "config", "compare_prompt_template.md")
# 仓库内置样例（与 cfg.example 类似，可纳入版本库供复制参考）
COMPARE_PROMPT_EXAMPLE_FILE = os.path.join(
    SCRIPT_DIR, "config", "compare_prompt_template.example.md"
)
# 旧版 .txt，仅用于迁移读取
_COMPARE_PROMPT_FILE_LEGACY = os.path.join(SCRIPT_DIR, "config", "compare_prompt_template.txt")


def _load_compare_prompt_from_file():
    """读取比较提示词：用户 md → 旧 txt → 样例 example.md → None"""
    for path in (
        COMPARE_PROMPT_FILE,
        _COMPARE_PROMPT_FILE_LEGACY,
        COMPARE_PROMPT_EXAMPLE_FILE,
    ):
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            if text.strip():
                return text
        except Exception:
            continue
    return None


def _save_compare_prompt_to_file(text: str) -> None:
    """将比较提示词写入本地 Markdown 文件（与 summary_generation.cfg 同目录）。"""
    try:
        os.makedirs(os.path.dirname(COMPARE_PROMPT_FILE), exist_ok=True)
        with open(COMPARE_PROMPT_FILE, "w", encoding="utf-8") as f:
            f.write(text or "")
    except Exception:
        pass


# 默认提示词模板
DEFAULT_PROMPT_TEMPLATE = """请判断以下待评估内容是否符合标准答案。

标准答案（Reference）：
{reference}

待评估内容（Candidate）：
{candidate}

请以JSON格式输出评估结果，格式如下：
{{
    "result": "正确" 或 "错误",
    "reason": "简短的判定理由"
}}"""


def _load_persisted_llm_config():
    """从 summary_generation.cfg 中加载比较模型相关的 LLM 配置到 session_state。"""
    if not os.path.exists(CONFIG_FILE):
        return

    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE, encoding="utf-8")
    except Exception:
        return

    # LLM配置-比较模型
    if config.has_section("LLM配置-比较模型"):
        section = "LLM配置-比较模型"
        st.session_state.api_key = config.get(section, "compare_api_key", fallback=st.session_state.api_key)
        st.session_state.api_base_url = config.get(section, "compare_base_url", fallback=st.session_state.api_base_url)
        st.session_state.model_name = config.get(section, "compare_model", fallback=st.session_state.model_name)
        st.session_state.temperature = config.getfloat(section, "compare_temperature", fallback=st.session_state.temperature)
        # 并发线程数来自 性能配置
        if config.has_section("性能配置"):
            st.session_state.max_workers = config.getint("性能配置", "max_workers", fallback=st.session_state.max_workers)

    # 鉴权配置-比较模型
    if config.has_section("鉴权配置-比较模型"):
        section = "鉴权配置-比较模型"
        st.session_state.enable_auth = config.getboolean(section, "enable_auth", fallback=st.session_state.enable_auth)
        st.session_state.calculate_auth = config.getboolean(section, "calculate_auth", fallback=st.session_state.calculate_auth)
        st.session_state.authorization = config.get(section, "authorization", fallback=st.session_state.authorization)
        st.session_state.app_key = config.get(section, "app_key", fallback=st.session_state.app_key)
        st.session_state.app_secret = config.get(section, "app_secret", fallback=st.session_state.app_secret)
        st.session_state.source = config.get(section, "source", fallback=st.session_state.source)
        st.session_state.org_id = config.get(section, "org_id", fallback=st.session_state.org_id)
        st.session_state.org_name = config.get(section, "org_name", fallback=st.session_state.org_name)
        st.session_state.full_org_name = config.get(section, "full_org_name", fallback=st.session_state.full_org_name)
        st.session_state.oa_code = config.get(section, "oa_code", fallback=st.session_state.oa_code)
        st.session_state.user_name = config.get(section, "user_name", fallback=st.session_state.user_name)


def _save_persisted_llm_config_from_state():
    """将当前侧边栏中的比较模型 LLM 配置写回 summary_generation.cfg。"""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        try:
            config.read(CONFIG_FILE, encoding="utf-8")
        except Exception:
            # 读取失败则从空配置开始
            config = configparser.ConfigParser()

    # 确保相关 section 存在
    if not config.has_section("LLM配置-比较模型"):
        config.add_section("LLM配置-比较模型")
    if not config.has_section("鉴权配置-比较模型"):
        config.add_section("鉴权配置-比较模型")
    if not config.has_section("性能配置"):
        config.add_section("性能配置")

    # 写入 LLM配置-比较模型
    section = "LLM配置-比较模型"
    config.set(section, "compare_api_key", st.session_state.api_key or "")
    config.set(section, "compare_base_url", st.session_state.api_base_url or "")
    config.set(section, "compare_model", st.session_state.model_name or "")
    config.set(section, "compare_temperature", str(st.session_state.temperature))
    # compare_top_p 保持原值（如需调整可后续在 UI 中扩展）

    # 写入 鉴权配置-比较模型
    section = "鉴权配置-比较模型"
    config.set(section, "enable_auth", "True" if st.session_state.enable_auth else "False")
    config.set(section, "calculate_auth", "True" if st.session_state.calculate_auth else "False")
    config.set(section, "authorization", st.session_state.authorization or "")
    config.set(section, "app_key", st.session_state.app_key or "")
    config.set(section, "app_secret", st.session_state.app_secret or "")
    config.set(section, "source", st.session_state.source or "")
    config.set(section, "org_id", st.session_state.org_id or "")
    config.set(section, "org_name", st.session_state.org_name or "")
    config.set(section, "full_org_name", st.session_state.full_org_name or "")
    config.set(section, "oa_code", st.session_state.oa_code or "")
    config.set(section, "user_name", st.session_state.user_name or "")

    # 写入 性能配置（只同步 max_workers）
    section = "性能配置"
    config.set(section, "max_workers", str(st.session_state.max_workers))

    # 保存到文件
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        config.write(f)


def load_config():
    """从session_state加载配置，如果不存在则使用默认值，并在首次运行时尝试从cfg文件恢复持久化配置"""
    if 'api_base_url' not in st.session_state:
        st.session_state.api_base_url = ""
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    if 'model_name' not in st.session_state:
        st.session_state.model_name = ""
    if 'temperature' not in st.session_state:
        st.session_state.temperature = 0.0
    if 'max_tokens' not in st.session_state:
        st.session_state.max_tokens = 512
    if 'max_workers' not in st.session_state:
        st.session_state.max_workers = 5
    # 鉴权相关默认配置
    if 'enable_auth' not in st.session_state:
        st.session_state.enable_auth = False
    if 'calculate_auth' not in st.session_state:
        st.session_state.calculate_auth = True
    if 'authorization' not in st.session_state:
        st.session_state.authorization = ""
    if 'app_key' not in st.session_state:
        st.session_state.app_key = ""
    if 'app_secret' not in st.session_state:
        st.session_state.app_secret = ""
    if 'source' not in st.session_state:
        st.session_state.source = ""
    if 'org_id' not in st.session_state:
        st.session_state.org_id = ""
    if 'org_name' not in st.session_state:
        st.session_state.org_name = ""
    if 'full_org_name' not in st.session_state:
        st.session_state.full_org_name = ""
    if 'oa_code' not in st.session_state:
        st.session_state.oa_code = ""
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""

    # 比较提示词：会话内用固定 key；首次从文件恢复，避免换上传文件后 text_area 被默认值覆盖
    if "compare_prompt_textarea" not in st.session_state:
        loaded = _load_compare_prompt_from_file()
        st.session_state.compare_prompt_textarea = (
            loaded if loaded else DEFAULT_PROMPT_TEMPLATE
        )

    # 首次加载时，从 summary_generation.cfg 里同步一份比较模型配置
    if 'config_loaded' not in st.session_state:
        _load_persisted_llm_config()
        st.session_state.config_loaded = True


def save_config():
    """保存配置到session_state（Streamlit会自动持久化）"""
    # Streamlit的session_state会在会话期间保持，但不会跨会话持久化
    # 如果需要真正的持久化，可以保存到文件或数据库
    pass


def process_single_row(
    row_data: Tuple[int, pd.Series, str, str, Dict]
) -> Tuple[int, str, str]:
    """
    处理单行数据
    
    Args:
        row_data: (row_index, row, reference_value, candidate_value, config)
    
    Returns:
        tuple: (row_index, result, reason)
    """
    row_idx, row, reference_value, candidate_value, config = row_data

    # 如果待评估列内容为空，则不调用LLM，标记为“跳过”，不计入准确率统计
    if not str(candidate_value).strip():
        # result 为空，reason 写明原因；calculate_accuracy 会自动跳过空 result
        return row_idx, "", "待评估内容为空，未处理（已跳过）"
    
    # 构建提示词
    prompt_template = config['prompt_template']
    prompt = prompt_template.format(
        reference=reference_value,
        candidate=candidate_value
    )
    
    # 强制追加JSON格式要求
    prompt += "\n\n请务必以JSON格式输出，格式为：{\"result\": \"正确\"或\"错误\", \"reason\": \"判定理由\"}"
    
    try:
        # 调用LLM（传入 row_idx 便于日志关联定位）
        response = call_llm(
            prompt=prompt,
            api_base_url=config['api_base_url'],
            api_key=config['api_key'],
            model_name=config['model_name'],
            temperature=config['temperature'],
            max_tokens=config['max_tokens'],
            auth_config=config.get('auth_config'),
            task_id=row_idx
        )
        
        # 解析响应
        result, reason = parse_llm_evaluation_response(response, task_id=row_idx)
        return row_idx, result, reason
        
    except Exception as e:
        error_msg = str(e)
        return row_idx, "Error", f"API调用失败: {error_msg}"


def main():
    # 延迟初始化数据库（在 main 函数中初始化，而不是模块导入时）
    ensure_database()
    
    st.title("🤖 LLM 自动化答案评估与对比工具")
    st.markdown("---")
    
    # 侧边栏：全局配置
    with st.sidebar:
        st.header("⚙️ 系统配置")
        
        # 加载配置
        load_config()
        
        # API配置
        st.subheader("LLM连接参数")
        api_base_url = st.text_input(
            "API Base URL",
            value=st.session_state.api_base_url,
            help="例如: https://api.deepseek.com/v1"
        )
        api_key = st.text_input(
            "API Key",
            value=st.session_state.api_key,
            type="password",
            help="API密钥"
        )
        model_name = st.text_input(
            "Model Name",
            value=st.session_state.model_name,
            help="例如: gpt-4o, deepseek-chat"
        )
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.temperature,
            step=0.1,
            help="温度参数，0.0保证评估一致性"
        )
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=1,
            max_value=4096,
            value=st.session_state.max_tokens,
            help="最大token数，防止输出截断"
        )
        max_workers = st.number_input(
            "并发线程数",
            min_value=1,
            max_value=20,
            value=st.session_state.max_workers,
            help="并发处理线程数"
        )

        # 鉴权配置
        with st.expander("🔐 鉴权配置（可选）", expanded=False):
            enable_auth = st.checkbox(
                "开启鉴权（HMAC-SHA1）",
                value=st.session_state.enable_auth,
                help="勾选后将使用HMAC-SHA1方式生成Authorization头；否则使用Bearer Token"
            )
            calculate_auth = st.checkbox(
                "自行计算 Authorization",
                value=st.session_state.calculate_auth,
                help="取消勾选时，将直接使用下方 Authorization 字段的值"
            )
            authorization = st.text_input(
                "Authorization（直传模式）",
                value=st.session_state.authorization,
                help="仅在【开启鉴权】且【不自行计算】时生效"
            )

            st.markdown("**签名参数（自行计算模式）**")
            app_key = st.text_input(
                "AppKey",
                value=st.session_state.app_key,
                help="密钥对的 key"
            )
            app_secret = st.text_input(
                "AppSecret",
                value=st.session_state.app_secret,
                type="password",
                help="密钥对的 Secret"
            )
            source = st.text_input(
                "Source（应用ID）",
                value=st.session_state.source,
                help="用于生成签名的 source 字段"
            )

            st.markdown("**用户信息（可选）**")
            org_id = st.text_input(
                "org_id",
                value=st.session_state.org_id
            )
            org_name = st.text_input(
                "org_name",
                value=st.session_state.org_name
            )
            full_org_name = st.text_input(
                "full_org_name",
                value=st.session_state.full_org_name
            )
            oa_code = st.text_input(
                "oa_code",
                value=st.session_state.oa_code
            )
            user_name = st.text_input(
                "user_name",
                value=st.session_state.user_name
            )
        
        # 保存配置按钮
        if st.button("💾 保存配置"):
            # 更新 session_state
            st.session_state.api_base_url = api_base_url
            st.session_state.api_key = api_key
            st.session_state.model_name = model_name
            st.session_state.temperature = temperature
            st.session_state.max_tokens = max_tokens
            st.session_state.max_workers = max_workers

            st.session_state.enable_auth = enable_auth
            st.session_state.calculate_auth = calculate_auth
            st.session_state.authorization = authorization
            st.session_state.app_key = app_key
            st.session_state.app_secret = app_secret
            st.session_state.source = source
            st.session_state.org_id = org_id
            st.session_state.org_name = org_name
            st.session_state.full_org_name = full_org_name
            st.session_state.oa_code = oa_code
            st.session_state.user_name = user_name

            # 写回 summary_generation.cfg，实现跨刷新持久化
            _save_persisted_llm_config_from_state()

            st.success("配置已保存！（已同步到 config/summary_generation.cfg 的比较模型配置）")
    
    # 主界面：任务配置
    st.header("📋 任务配置")
    
    # 步骤1: 数据加载
    st.subheader("步骤 1: 数据加载")
    uploaded_file = st.file_uploader(
        "上传CSV或Excel文件",
        type=['csv', 'xlsx'],
        help="支持.csv和.xlsx格式"
    )
    
    df = None
    sheet_name = None
    
    if uploaded_file is not None:
        file_ext = uploaded_file.name.split('.')[-1].lower()
        
        try:
            if file_ext == 'csv':
                # 尝试多种编码
                encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb18030']
                for encoding in encodings:
                    try:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                if df is None:
                    st.error("无法读取CSV文件，请检查文件编码")
            elif file_ext == 'xlsx':
                uploaded_file.seek(0)
                excel_file = pd.ExcelFile(uploaded_file)
                sheet_names = excel_file.sheet_names
                
                if len(sheet_names) > 1:
                    sheet_name = st.selectbox(
                        "选择要处理的Sheet",
                        sheet_names,
                        help="Excel文件包含多个Sheet，请选择要处理的一个"
                    )
                else:
                    sheet_name = sheet_names[0]
                
                df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
            
            if df is not None and not df.empty:
                st.success(f"✅ 文件加载成功！共 {len(df)} 行数据")
                st.dataframe(df.head(5), use_container_width=True)
            else:
                st.warning("文件为空或无法读取")
        except Exception as e:
            st.error(f"文件读取失败: {str(e)}")
    
    # 步骤2: 字段映射
    if df is not None and not df.empty:
        st.subheader("步骤 2: 字段映射")
        col1, col2 = st.columns(2)
        
        with col1:
            reference_column = st.selectbox(
                "选择标准答案列 (Reference Column)",
                df.columns.tolist(),
                help="作为真值基准的列"
            )
        
        with col2:
            candidate_column = st.selectbox(
                "选择待评估列 (Evaluation Column)",
                df.columns.tolist(),
                help="需要LLM评判的内容列"
            )
        
        col3, col4 = st.columns(2)
        with col3:
            result_column_name = st.text_input(
                "Result 列名",
                value="eval_result",
                help="评估结果列的名称"
            )
        with col4:
            reason_column_name = st.text_input(
                "Reason 列名",
                value="eval_reason",
                help="评估原因列的名称"
            )
        
        # 步骤3: 提示词模板（key 绑定 session_state，换文件不换内容；每次运行写回文件）
        st.subheader("步骤 3: 提示词模板")
        prompt_template = st.text_area(
            "提示词模板",
            height=200,
            key="compare_prompt_textarea",
            help="必须包含 {reference} 和 {candidate} 变量。系统会自动追加JSON格式要求。"
            "编辑内容保存到 config/compare_prompt_template.md；"
            "未改过前可从 config/compare_prompt_template.example.md 参考样例。",
        )
        _save_compare_prompt_to_file(prompt_template)
        
        # 验证提示词模板
        if "{reference}" not in prompt_template or "{candidate}" not in prompt_template:
            st.warning("⚠️ 提示词模板必须包含 {reference} 和 {candidate} 变量")
        
        # 开始评估按钮
        st.markdown("---")
        if st.button("▶️ 开始评估任务", type="primary", use_container_width=True):
            # 注意：st.button 不支持 width 参数，保留 use_container_width
            # 验证配置
            if not api_base_url or not api_key or not model_name:
                st.error("❌ 请先在侧边栏配置LLM连接参数！")
                return
            
            if reference_column == candidate_column:
                st.error("❌ 标准答案列和待评估列不能相同！")
                return
            
            # 准备鉴权配置
            auth_config = None
            if enable_auth:
                auth_config = {
                    "enable_auth": enable_auth,
                    "calculate_auth": calculate_auth,
                    "authorization": authorization,
                    "app_key": app_key,
                    "app_secret": app_secret,
                    "source": source,
                    "org_id": org_id,
                    "org_name": org_name,
                    "full_org_name": full_org_name,
                    "oa_code": oa_code,
                    "user_name": user_name,
                }

            # 准备配置
            config = {
                'api_base_url': api_base_url,
                'api_key': api_key,
                'model_name': model_name,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'prompt_template': prompt_template,
                'auth_config': auth_config,
            }
            
            # 初始化结果列
            if result_column_name not in df.columns:
                df[result_column_name] = ""
            if reason_column_name not in df.columns:
                df[reason_column_name] = ""
            
            # 准备任务数据（仅对“待评估列”非空的记录调用 LLM）
            tasks = []
            skipped_count = 0
            for idx, row in df.iterrows():
                reference_value = str(row[reference_column]) if pd.notna(row[reference_column]) else ""
                candidate_value = str(row[candidate_column]) if pd.notna(row[candidate_column]) else ""

                if not str(candidate_value).strip():
                    # 标记为跳过：不调用 LLM，也不计入处理记录数和准确率分母
                    df.at[idx, result_column_name] = ""
                    df.at[idx, reason_column_name] = "待评估内容为空，未处理（已跳过）"
                    skipped_count += 1
                    continue

                tasks.append((idx, row, reference_value, candidate_value, config))
            
            # 显示进度条
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 并发处理
            results = {}
            total_tasks = len(tasks)
            completed = 0

            if total_tasks == 0:
                # 没有任何有效待评估记录
                progress_bar.progress(1.0)
                status_text.text("未找到待评估内容非空的记录，全部已跳过。")
            else:
                # 长时间阻塞在单条 LLM 请求时，若不做周期性 UI 刷新，Streamlit 前端会因
                # WebSocket 长时间无更新而断连（Network issue / 页面无响应）。用带超时的
                # wait 在未完成时刷新状态，保持与浏览器的心跳。
                _heartbeat_sec = 2.0
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_idx = {
                        executor.submit(process_single_row, task): task[0]
                        for task in tasks
                    }
                    pending = set(future_to_idx.keys())
                    while pending:
                        done, pending = wait(
                            pending,
                            timeout=_heartbeat_sec,
                            return_when=FIRST_COMPLETED,
                        )
                        if not done:
                            status_text.text(
                                f"等待 API 响应中… 已完成 {completed}/{total_tasks} 条（不含跳过行）"
                            )
                            continue
                        for future in done:
                            try:
                                row_idx, result, reason = future.result()
                                results[row_idx] = (result, reason)
                            except Exception as e:
                                row_idx = future_to_idx[future]
                                results[row_idx] = ("Error", f"处理失败: {str(e)}")
                            completed += 1
                            progress_bar.progress(completed / total_tasks)
                            status_text.text(
                                f"正在处理第 {completed}/{total_tasks} 条（不含跳过行）..."
                            )
            
            # 回填结果
            for row_idx, (result, reason) in results.items():
                df.at[row_idx, result_column_name] = result
                df.at[row_idx, reason_column_name] = reason
            
            # 计算准确率
            stats = calculate_accuracy(df, result_column_name)
            
            # 统计“实际处理记录数”（真正提交给线程池的任务数，不含跳过）
            # 注意：这里直接使用 total_tasks，逻辑与构建 tasks 时完全一致，避免 NaN → 'nan' 这类字符串造成统计偏差
            processed_records = total_tasks

            # 显示统计结果
            st.success("✅ 评估完成！")
            st.markdown("### 📊 统计结果")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("准确率", f"{stats['accuracy']:.2%}")
            with col2:
                st.metric("正确数", stats['correct_count'])
            with col3:
                st.metric("错误数", stats['incorrect_count'])
            with col4:
                st.metric("错误/异常", stats['error_count'])
            st.caption(f"实际处理记录数（待评估列非空）: {processed_records}，跳过记录数: {skipped_count}")
            
            # 显示结果表格
            st.markdown("### 📋 评估结果")
            st.dataframe(df, use_container_width=True)
            
            # 生成下载文件
            output = io.BytesIO()
            file_ext = uploaded_file.name.split('.')[-1].lower()
            
            if file_ext == 'xlsx':
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # 写入主数据
                    df.to_excel(writer, sheet_name='评估结果', index=False)
                    
                    # 写入统计信息
                    stats_df = pd.DataFrame([{
                        '指标': '准确率',
                        '值': f"{stats['accuracy']:.2%}"
                    }, {
                        '指标': '正确数',
                        '值': stats['correct_count']
                    }, {
                        '指标': '错误数',
                        '值': stats['incorrect_count']
                    }, {
                        '指标': '错误/异常数',
                        '值': stats['error_count']
                    }, {
                        '指标': '有效总数',
                        '值': stats['total_valid']
                    }])
                    stats_df.to_excel(writer, sheet_name='统计信息', index=False)
            else:
                # CSV格式
                df.to_csv(output, index=False, encoding='utf-8-sig')
            
            output.seek(0)
            
            # 下载按钮
            download_filename = f"eval_result_{uploaded_file.name}"
            st.download_button(
                label="📥 下载评估结果",
                data=output,
                file_name=download_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if file_ext == 'xlsx' else "text/csv",
                use_container_width=True  # st.download_button 不支持 width 参数
            )
            
            # 保存历史记录（records 使用“实际处理记录数”，不含跳过行）
            # 注意：processed_records 只包含待评估列非空的记录，不包含被跳过的空记录
            columns_info = f"Ref: [{reference_column}] vs Eval: [{candidate_column}]"
            save_eval_history(
                file=uploaded_file.name,
                columns=columns_info,
                model=model_name,
                records=processed_records,  # 不含跳过的记录数
                accuracy=stats['accuracy'],
                prompt=prompt_template
            )
    
    # 历史记录
    st.markdown("---")
    st.header("📜 历史记录")
    
    history = get_eval_history(limit=50)
    if history:
        history_df = pd.DataFrame(history)
        # 格式化准确率显示
        history_df['准确率'] = history_df['accuracy'].apply(
            lambda x: f"{x:.2%}" if pd.notna(x) else "N/A"
        )
        # 重命名记录数字段，明确为“处理记录数(不含跳过)”
        # 注意：数据库中的 records 字段存储的就是不含跳过的实际处理记录数
        history_df = history_df.rename(columns={"records": "处理记录数(不含跳过)"})
        # 选择显示的列
        display_columns = ['time', 'file', 'columns', 'model', '处理记录数(不含跳过)', '准确率']
        st.dataframe(
            history_df[display_columns],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("暂无历史记录")


if __name__ == "__main__":
    main()
