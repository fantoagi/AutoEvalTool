import os
import sys
import csv
import json
import time
import glob
import re
import random
import urllib.request
import urllib.error
import urllib.parse
import threading
import configparser
import hmac
import hashlib
import base64
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import pandas as pd
    try:
        import openpyxl  # type: ignore[import-untyped]
        EXCEL_AVAILABLE = True
    except ImportError:
        EXCEL_AVAILABLE = False
        print("警告: openpyxl 未安装，将使用CSV格式输出。如需Excel输出，请安装: pip install openpyxl")
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    EXCEL_AVAILABLE = False
    print("警告: pandas 未安装，将使用CSV格式输出。如需Excel输出，请安装: pip install pandas openpyxl")

# Try to import tqdm for progress bar, otherwise use a dummy
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, desc=None, unit=None):
        print(f"Start processing: {desc}")
        return iterable

# 获取脚本所在目录（兼容PyInstaller打包后的环境）
if getattr(sys, 'frozen', False):
    # PyInstaller打包后的环境：使用可执行文件所在目录
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    # 开发环境：使用脚本文件所在目录
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置文件路径
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config", "summary_generation.cfg")

# 配置变量（将从配置文件加载）
API_KEY = ""
BASE_URL = ""
MODEL = ""
TEMPERATURE = 0.7
TOP_P = 0.9

COMPARE_API_KEY = ""
COMPARE_BASE_URL = ""
COMPARE_MODEL = ""
COMPARE_TEMPERATURE = 0.7
COMPARE_TOP_P = 0.9

PROMPT_DIR = ""
CSV_DIR = ""
RESULT_DIR = ""
PROMPT_FILE = ""
COMPARE_PROMPT_FILE = ""
PROMPT_FILE_NAME = ""
COMPARE_PROMPT_FILE_NAME = ""
CSV_FILE_NAME = ""
MAX_WORKERS = 5
SAMPLE_SIZE = 0  # 随机抽取数量，0表示处理全部
LOG_FILE = os.path.join(SCRIPT_DIR, "process.log")
SUMMARY_LOG_FILE = os.path.join(SCRIPT_DIR, "summary.log")
OUTPUT_FORMAT = "csv"  # 输出格式：csv 或 excel

# 鉴权配置-主模型
MAIN_ENABLE_AUTH = False
MAIN_CALCULATE_AUTH = True
MAIN_AUTHORIZATION = ""
MAIN_APP_KEY = ""
MAIN_APP_SECRET = ""
MAIN_SOURCE = ""
MAIN_ORG_ID = ""
MAIN_ORG_NAME = ""
MAIN_FULL_ORG_NAME = ""
MAIN_OA_CODE = ""
MAIN_USER_NAME = ""

# 鉴权配置-比较模型
COMPARE_ENABLE_AUTH = False
COMPARE_CALCULATE_AUTH = True
COMPARE_AUTHORIZATION = ""
COMPARE_APP_KEY = ""
COMPARE_APP_SECRET = ""
COMPARE_SOURCE = ""
COMPARE_ORG_ID = ""
COMPARE_ORG_NAME = ""
COMPARE_FULL_ORG_NAME = ""
COMPARE_OA_CODE = ""
COMPARE_USER_NAME = ""

def load_config():
    """从配置文件加载所有配置"""
    global API_KEY, BASE_URL, MODEL, TEMPERATURE, TOP_P
    global COMPARE_API_KEY, COMPARE_BASE_URL, COMPARE_MODEL, COMPARE_TEMPERATURE, COMPARE_TOP_P
    global PROMPT_DIR, CSV_DIR, RESULT_DIR, PROMPT_FILE, COMPARE_PROMPT_FILE, PROMPT_FILE_NAME, COMPARE_PROMPT_FILE_NAME, CSV_FILE_NAME, MAX_WORKERS, SAMPLE_SIZE, OUTPUT_FORMAT
    global MAIN_ENABLE_AUTH, MAIN_CALCULATE_AUTH, MAIN_AUTHORIZATION, MAIN_APP_KEY, MAIN_APP_SECRET, MAIN_SOURCE
    global MAIN_ORG_ID, MAIN_ORG_NAME, MAIN_FULL_ORG_NAME, MAIN_OA_CODE, MAIN_USER_NAME
    global COMPARE_ENABLE_AUTH, COMPARE_CALCULATE_AUTH, COMPARE_AUTHORIZATION, COMPARE_APP_KEY, COMPARE_APP_SECRET, COMPARE_SOURCE
    global COMPARE_ORG_ID, COMPARE_ORG_NAME, COMPARE_FULL_ORG_NAME, COMPARE_OA_CODE, COMPARE_USER_NAME
    
    if not os.path.exists(CONFIG_FILE):
        print(f"错误: 配置文件不存在: {CONFIG_FILE}")
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_FILE}")
    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    
    # 文件路径配置
    CSV_DIR = os.path.join(SCRIPT_DIR, config.get('文件路径', 'csv_dir', fallback='CSV'))
    result_dir_config = config.get('文件路径', 'result_dir', fallback='')
    if result_dir_config and result_dir_config.strip():
        RESULT_DIR = os.path.join(SCRIPT_DIR, result_dir_config.strip())
    else:
        # 如果未配置，使用CSV目录
        RESULT_DIR = CSV_DIR
    PROMPT_DIR = os.path.join(SCRIPT_DIR, config.get('文件路径', 'prompt_dir', fallback='辅助小结'))
    
    PROMPT_FILE_NAME = config.get('文件路径', 'prompt_file_name', fallback='prompt.md')
    COMPARE_PROMPT_FILE_NAME = config.get('文件路径', 'compare_prompt_file_name', fallback='compare.md')
    CSV_FILE_NAME = config.get('文件路径', 'csv_file_name', fallback='')
    
    PROMPT_FILE = os.path.join(PROMPT_DIR, PROMPT_FILE_NAME)
    COMPARE_PROMPT_FILE = os.path.join(PROMPT_DIR, COMPARE_PROMPT_FILE_NAME)
    
    # LLM配置-主模型
    API_KEY = config.get('LLM配置-主模型', 'api_key', fallback='')
    BASE_URL = config.get('LLM配置-主模型', 'base_url', fallback='')
    MODEL = config.get('LLM配置-主模型', 'model', fallback='')
    TEMPERATURE = config.getfloat('LLM配置-主模型', 'temperature', fallback=0.7)
    TOP_P = config.getfloat('LLM配置-主模型', 'top_p', fallback=0.9)
    
    # LLM配置-比较模型
    COMPARE_API_KEY = config.get('LLM配置-比较模型', 'compare_api_key', fallback='')
    COMPARE_BASE_URL = config.get('LLM配置-比较模型', 'compare_base_url', fallback='')
    COMPARE_MODEL = config.get('LLM配置-比较模型', 'compare_model', fallback='')
    COMPARE_TEMPERATURE = config.getfloat('LLM配置-比较模型', 'compare_temperature', fallback=0.7)
    COMPARE_TOP_P = config.getfloat('LLM配置-比较模型', 'compare_top_p', fallback=0.9)
    
    # 鉴权配置-主模型
    MAIN_ENABLE_AUTH = config.getboolean('鉴权配置-主模型', 'enable_auth', fallback=False)
    MAIN_CALCULATE_AUTH = config.getboolean('鉴权配置-主模型', 'calculate_auth', fallback=True)
    MAIN_AUTHORIZATION = config.get('鉴权配置-主模型', 'authorization', fallback='')
    MAIN_APP_KEY = config.get('鉴权配置-主模型', 'app_key', fallback='')
    MAIN_APP_SECRET = config.get('鉴权配置-主模型', 'app_secret', fallback='')
    MAIN_SOURCE = config.get('鉴权配置-主模型', 'source', fallback='')
    MAIN_ORG_ID = config.get('鉴权配置-主模型', 'org_id', fallback='')
    MAIN_ORG_NAME = config.get('鉴权配置-主模型', 'org_name', fallback='')
    MAIN_FULL_ORG_NAME = config.get('鉴权配置-主模型', 'full_org_name', fallback='')
    MAIN_OA_CODE = config.get('鉴权配置-主模型', 'oa_code', fallback='')
    MAIN_USER_NAME = config.get('鉴权配置-主模型', 'user_name', fallback='')
    
    # 鉴权配置-比较模型
    COMPARE_ENABLE_AUTH = config.getboolean('鉴权配置-比较模型', 'enable_auth', fallback=False)
    COMPARE_CALCULATE_AUTH = config.getboolean('鉴权配置-比较模型', 'calculate_auth', fallback=True)
    COMPARE_AUTHORIZATION = config.get('鉴权配置-比较模型', 'authorization', fallback='')
    COMPARE_APP_KEY = config.get('鉴权配置-比较模型', 'app_key', fallback='')
    COMPARE_APP_SECRET = config.get('鉴权配置-比较模型', 'app_secret', fallback='')
    COMPARE_SOURCE = config.get('鉴权配置-比较模型', 'source', fallback='')
    COMPARE_ORG_ID = config.get('鉴权配置-比较模型', 'org_id', fallback='')
    COMPARE_ORG_NAME = config.get('鉴权配置-比较模型', 'org_name', fallback='')
    COMPARE_FULL_ORG_NAME = config.get('鉴权配置-比较模型', 'full_org_name', fallback='')
    COMPARE_OA_CODE = config.get('鉴权配置-比较模型', 'oa_code', fallback='')
    COMPARE_USER_NAME = config.get('鉴权配置-比较模型', 'user_name', fallback='')
    
    # 性能配置
    MAX_WORKERS = config.getint('性能配置', 'max_workers', fallback=5)
    SAMPLE_SIZE = config.getint('性能配置', 'sample_size', fallback=0)
    
    # 输出配置
    OUTPUT_FORMAT = config.get('输出配置', 'output_format', fallback='csv').lower()
    if OUTPUT_FORMAT not in ['csv', 'excel']:
        print(f"警告: 输出格式 '{OUTPUT_FORMAT}' 无效，使用默认值 'csv'")
        OUTPUT_FORMAT = 'csv'
    
    print(f"配置加载成功: {CONFIG_FILE}")

def encode_payload_string(payload_str):
    """将payload字符串编码为Base64并URL编码"""
    # 转换为UTF-8字节
    payload_bytes = payload_str.encode('utf-8')
    # Base64编码
    base64_encoded = base64.b64encode(payload_bytes).decode('utf-8')
    # URL编码
    url_encoded = urllib.parse.quote(base64_encoded)
    return url_encoded

def generate_auth_headers(model_type="main"):
    """生成鉴权headers（Source, X-Date, Authorization, X-Custom-Payload）
    
    Args:
        model_type: "main" 表示主模型，"compare" 表示比较模型
    """
    # 根据模型类型选择对应的鉴权配置
    if model_type == "compare":
        enable_auth = COMPARE_ENABLE_AUTH
        calculate_auth = COMPARE_CALCULATE_AUTH
        authorization = COMPARE_AUTHORIZATION
        app_key = COMPARE_APP_KEY
        app_secret = COMPARE_APP_SECRET
        source = COMPARE_SOURCE
        org_id = COMPARE_ORG_ID
        org_name = COMPARE_ORG_NAME
        full_org_name = COMPARE_FULL_ORG_NAME
        oa_code = COMPARE_OA_CODE
        user_name = COMPARE_USER_NAME
    else:  # main
        enable_auth = MAIN_ENABLE_AUTH
        calculate_auth = MAIN_CALCULATE_AUTH
        authorization = MAIN_AUTHORIZATION
        app_key = MAIN_APP_KEY
        app_secret = MAIN_APP_SECRET
        source = MAIN_SOURCE
        org_id = MAIN_ORG_ID
        org_name = MAIN_ORG_NAME
        full_org_name = MAIN_FULL_ORG_NAME
        oa_code = MAIN_OA_CODE
        user_name = MAIN_USER_NAME
    
    if not enable_auth:
        return {}
    
    # 如果不需要自行计算，直接使用配置的authorization值
    if not calculate_auth:
        if authorization:
            return {'Authorization': authorization}
        else:
            print(f"警告: {model_type}模型 calculate_auth=False 但 authorization 为空，将使用Bearer Token")
            return {}
    
    # 自行计算authorization（原有逻辑）
    # 生成payload
    if org_id or org_name or full_org_name or oa_code or user_name:
        # OA用户或自建用户
        payload_dict = {
            "orgId": org_id,
            "orgName": org_name,
            "fullOrgName": full_org_name,
            "oaCode": oa_code,
            "userName": user_name
        }
        payload_str = json.dumps(payload_dict, ensure_ascii=False)
    else:
        # 无用户接入
        payload_str = "{}"
    
    # 编码payload
    custom_payload = encode_payload_string(payload_str)
    
    # 获取当前GMT时间（使用timezone-aware方式，修复弃用警告）
    try:
        # Python 3.11+
        now = datetime.now(datetime.UTC)
    except AttributeError:
        # Python 3.9-3.10 兼容
        now = datetime.now(timezone.utc)
    date_time = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    # 生成签名字符串
    sign_str = f"x-date: {date_time}\nsource: {source}\nx-custom-payload: {custom_payload}"
    
    # HMAC-SHA1签名
    signature = hmac.new(
        app_secret.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha1
    ).digest()
    
    # Base64编码签名
    signature_base64 = base64.b64encode(signature).decode('utf-8')
    
    # 生成Authorization header
    auth_str = f'hmac username="{app_key}", algorithm="hmac-sha1", headers="x-date source x-custom-payload", signature="{signature_base64}"'
    
    # 返回headers
    headers = {
        'Source': source,
        'X-Date': date_time,
        'Authorization': auth_str,
        'X-Custom-Payload': custom_payload
    }
    
    return headers

def call_llm(prompt):
    """Call LLM API to get the summary."""
    # 构建headers
    headers = {"Content-Type": "application/json"}
    
    # 如果启用鉴权，使用HMAC-SHA1鉴权（主模型）
    if MAIN_ENABLE_AUTH:
        auth_headers = generate_auth_headers("main")
        headers.update(auth_headers)
    else:
        # 否则使用Bearer Token
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    # 构建请求数据
    data = {
        "model": MODEL, 
        "messages": [
            {"role": "user", "content": prompt}
        ], 
        "stream": False,
        "enable_thinking": False,
    }
    
    # 添加temperature和top_p参数
    if TEMPERATURE is not None:
        data["temperature"] = TEMPERATURE
    if TOP_P is not None:
        data["top_p"] = TOP_P
    
    # 记录请求
    try:
        req_body_str = json.dumps(data, ensure_ascii=False)
        log_llm_detail("===== LLM 请求开始 =====")
        log_llm_detail(f"URL: {BASE_URL}")
        log_llm_detail(f"Model: {MODEL}")
        log_llm_detail(f"Temperature: {TEMPERATURE}")
        log_llm_detail(f"Top-P: {TOP_P}")
        log_llm_detail(f"Headers: {json.dumps(headers, ensure_ascii=False)}")
        log_llm_detail(f"Request Body: {req_body_str}")
    except Exception as e:
        print(f"Warning: failed to log LLM request: {e}")

    try:
        req = urllib.request.Request(BASE_URL, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=60) as res:
            raw = res.read().decode('utf-8')

            # 记录响应
            try:
                log_llm_detail("===== LLM 响应开始 =====")
                log_llm_detail(f"Raw Response: {raw}")
                log_llm_detail("===== LLM 响应结束 =====")
            except Exception as e:
                print(f"Warning: failed to log LLM response: {e}")

            response = json.loads(raw)
            return response['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        raise Exception(f"HTTP Error {e.code}: {err_body}")
    except Exception as e:
        raise Exception(f"API Error: {e}")


def call_compare_llm(prompt):
    """Call LLM API for compare step (独立配置，用于一致性判断)."""
    # 构建headers
    headers = {"Content-Type": "application/json"}
    
    # 如果启用鉴权，使用HMAC-SHA1鉴权（比较模型）
    if COMPARE_ENABLE_AUTH:
        auth_headers = generate_auth_headers("compare")
        headers.update(auth_headers)
    else:
        # 否则使用Bearer Token
        headers["Authorization"] = f"Bearer {COMPARE_API_KEY}"
    
    # 构建请求数据
    data = {
        "model": COMPARE_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "enable_thinking": False,
    }
    
    # 添加temperature和top_p参数
    if COMPARE_TEMPERATURE is not None:
        data["temperature"] = COMPARE_TEMPERATURE
    if COMPARE_TOP_P is not None:
        data["top_p"] = COMPARE_TOP_P

    # 记录请求
    try:
        req_body_str = json.dumps(data, ensure_ascii=False)
        log_llm_detail("===== Compare LLM 请求开始 =====")
        log_llm_detail(f"URL: {COMPARE_BASE_URL}")
        log_llm_detail(f"Model: {COMPARE_MODEL}")
        log_llm_detail(f"Temperature: {COMPARE_TEMPERATURE}")
        log_llm_detail(f"Top-P: {COMPARE_TOP_P}")
        log_llm_detail(f"Headers: {json.dumps(headers, ensure_ascii=False)}")
        log_llm_detail(f"Request Body: {req_body_str}")
    except Exception as e:
        print(f"Warning: failed to log Compare LLM request: {e}")

    try:
        req = urllib.request.Request(COMPARE_BASE_URL, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=60) as res:
            raw = res.read().decode('utf-8')

            # 记录响应
            try:
                log_llm_detail("===== Compare LLM 响应开始 =====")
                log_llm_detail(f"Raw Response: {raw}")
                log_llm_detail("===== Compare LLM 响应结束 =====")
            except Exception as e:
                print(f"Warning: failed to log Compare LLM response: {e}")

            response = json.loads(raw)
            return response['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        raise Exception(f"Compare HTTP Error {e.code}: {err_body}")
    except Exception as e:
        raise Exception(f"Compare API Error: {e}")

def parse_llm_response(response_text):
    """Parse the JSON response from LLM."""
    try:
        # Try to find JSON block if wrapped in markdown code blocks
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "```" in response_text:
             start = response_text.find("```") + 3
             end = response_text.find("```", start)
             json_str = response_text[start:end].strip()
        else:
            json_str = response_text.strip()
        
        data = json.loads(json_str)
        return data.get("辅助小结", response_text)
    except json.JSONDecodeError:
        # If not valid JSON, return the raw text or try to extract if it's mixed
        return response_text.strip()

# 日志写入锁，确保多线程环境下日志写入的线程安全
_log_lock = threading.Lock()

def log_error(filename, row_idx, error_msg):
    """Log errors to a file (thread-safe)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _log_lock:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] File: {filename}, Row: {row_idx}, Error: {error_msg}\n")
        except Exception as e:
            print(f"Warning: failed to write error log: {e}")


def log_llm_detail(message: str):
    """Log detailed LLM request/response to the same log file (thread-safe)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _log_lock:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            # 避免因为日志写入失败影响主流程
            print(f"Warning: failed to write LLM log: {e}")

def process_single_row(row_data):
    """处理单行数据的函数（用于多线程处理）"""
    row_idx, row, filename, prompt_template, compare_template = row_data
    
    # Ensure row has enough columns (至少到第 6 列)
    while len(row) < 6:
        row.append("")
        
    dialogue_content = row[1]  # 2nd column: 对话内容
    
    # Skip if empty input
    if not dialogue_content.strip():
        return row_idx, row, False, False  # (row_idx, row, success, failed)
    
    # Construct prompt
    full_prompt = f"{prompt_template}\n\n##对话文本\n\n{dialogue_content}"
    
    success = False
    failed = False
    
    try:
        llm_output = call_llm(full_prompt)
        summary = parse_llm_response(llm_output)
        # 写入第 4 列（索引 3）：辅助小结(llm生成)
        row[3] = summary
        success = True
    except Exception as e:
        error_msg = str(e)
        log_error(filename, row_idx + 1, error_msg)
        row[3] = "[ERROR]"
        failed = True

    # === 额外一次调用：compare 辅助小结一致性（第 3 列 vs 第 4 列），结果拆分为第 5 列（评估结果）和第 6 列（评估理由） ===
    try:
        source_text = (row[2] or "").strip() if len(row) > 2 else ""
        dest_text = (row[3] or "").strip() if len(row) > 3 else ""
        if source_text and dest_text and compare_template:
            compare_prompt = (
                compare_template.replace("{{source}}", source_text).replace("{{dest}}", dest_text)
            )
            # 使用独立的比较模型调用
            compare_result = call_compare_llm(compare_prompt)
            if compare_result:
                # 解析JSON格式的比较结果
                try:
                    # 尝试解析JSON
                    clean_json = compare_result.replace("```json", "").replace("```", "").strip()
                    # 尝试提取JSON对象
                    match = re.search(r'\{.*\}', clean_json, re.DOTALL)
                    if match:
                        clean_json = match.group(0)
                    data = json.loads(clean_json)
                    # 提取评估结果和评估理由
                    evaluation_result = data.get("评估结果", "").strip()
                    evaluation_reason = data.get("评估理由", "").strip()
                    # 确保行有足够的列
                    while len(row) < 6:
                        row.append("")
                    # 写入第5列（评估结果）和第6列（评估理由）
                    row[4] = evaluation_result
                    row[5] = evaluation_reason
                except (json.JSONDecodeError, KeyError, AttributeError) as e:
                    # 如果JSON解析失败，将原始结果写入第5列，第6列留空
                    while len(row) < 6:
                        row.append("")
                    row[4] = compare_result.strip()
                    row[5] = f"JSON Parse Error: {str(e)}"
                    log_error(filename, row_idx + 1, f"Compare JSON Parse Error: {e}")
    except Exception as e:
        # 出错时仅记录日志，不影响主流程
        error_msg = f"Compare Error: {e}"
        log_error(filename, row_idx + 1, error_msg)
        # 确保行有足够的列
        while len(row) < 6:
            row.append("")
    
    return row_idx, row, success, failed


def log_summary(process_time, csv_filename, output_filename, prompt_filename, accuracy_stats, sample_size=None, total_rows=None, 
                main_model=None, main_temperature=None, main_top_p=None, 
                compare_model=None, compare_temperature=None, compare_top_p=None):
    """记录处理结果到summary.log文件（线程安全）"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _log_lock:
        try:
            with open(SUMMARY_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] 处理完成\n")
                f.write(f"  处理时间: {process_time}\n")
                f.write(f"  处理的CSV文件名: {csv_filename}\n")
                f.write(f"  输出文件名: {output_filename}\n")
                f.write(f"  提示词文件名: {prompt_filename}\n")
                if sample_size is not None and total_rows is not None:
                    if sample_size > 0:
                        f.write(f"  随机抽取数量: {sample_size} (总记录数: {total_rows})\n")
                    else:
                        f.write(f"  处理记录数: {total_rows} (全部记录)\n")
                # 记录LLM配置信息
                if main_model is not None:
                    f.write(f"  LLM配置-主模型:\n")
                    f.write(f"    - 模型名称: {main_model}\n")
                    if main_temperature is not None:
                        f.write(f"    - Temperature: {main_temperature}\n")
                    if main_top_p is not None:
                        f.write(f"    - Top-P: {main_top_p}\n")
                if compare_model is not None:
                    f.write(f"  LLM配置-比较模型:\n")
                    f.write(f"    - 模型名称: {compare_model}\n")
                    if compare_temperature is not None:
                        f.write(f"    - Temperature: {compare_temperature}\n")
                    if compare_top_p is not None:
                        f.write(f"    - Top-P: {compare_top_p}\n")
                if accuracy_stats:
                    f.write(f"  准确率统计结果:\n")
                    for stat in accuracy_stats:
                        f.write(f"    - {stat['比较类型']}: {stat['准确率']} (正确: {stat['正确的记录数']}, 错误: {stat['错误的记录数']}, 总计: {stat['总记录数']})\n")
                else:
                    f.write(f"  准确率统计结果: 无\n")
                f.write("\n")
        except Exception as e:
            print(f"警告: 无法写入summary.log: {e}")

def process_file(file_path, prompt_template, compare_template):
    filename = os.path.basename(file_path)
    print(f"Processing file: {filename} (using {MAX_WORKERS} threads)")
    
    rows = []
    encoding = 'utf-8'
    
    # Try reading with multiple encodings
    encodings_to_try = ['utf-8', 'utf-8-sig', 'gbk', 'gb18030', 'latin-1', 'cp1252']
    for enc in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                rows = list(csv.reader(f))
            encoding = enc
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        # If all encodings fail, try with errors='ignore' or 'replace'
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                rows = list(csv.reader(f))
            encoding = 'utf-8'
            print(f"Warning: File {filename} had encoding issues, using error replacement mode.")
        except Exception as e:
            print(f"Error: Could not read file {filename} with any encoding: {e}")
            return 0, 0
            
    if not rows:
        print(f"Skipping empty file: {filename}")
        return 0, 0

    # Ensure header has the target columns
    header = rows[0]
    
    # 随机抽取逻辑
    data_rows = rows[1:]  # 数据行（排除表头）
    total_rows_count = len(data_rows)
    sampled_rows = data_rows
    actual_sample_size = 0  # 实际抽取的数量（用于日志记录）
    
    if SAMPLE_SIZE > 0 and total_rows_count > 0:
        # 如果设置了抽取数量，进行随机抽取
        if SAMPLE_SIZE >= total_rows_count:
            # 如果抽取数量大于等于总记录数，使用全部记录
            print(f"  抽取数量 ({SAMPLE_SIZE}) 大于等于总记录数 ({total_rows_count})，处理全部记录")
            actual_sample_size = total_rows_count
        else:
            # 随机抽取指定数量的记录
            sampled_rows = random.sample(data_rows, SAMPLE_SIZE)
            actual_sample_size = SAMPLE_SIZE
            print(f"  从 {total_rows_count} 条记录中随机抽取 {SAMPLE_SIZE} 条进行处理")
    else:
        actual_sample_size = total_rows_count  # 处理全部记录
    
    # 重新组装rows（表头 + 抽取的数据行）
    rows = [header] + sampled_rows
    
    # 设置表头列名
    if len(header) < 6:
        header.extend([""] * (6 - len(header)))
    
    if not header[3]:
        header[3] = "辅助小结(llm生成)"
    if not header[4]:
        header[4] = "评估结果"
    if not header[5]:
        header[5] = "评估理由"
    
    # 准备多线程处理的数据
    data_rows = rows[1:]  # 跳过表头
    row_tasks = [
        (i, rows[i + 1], filename, prompt_template, compare_template)
        for i in range(len(data_rows))
    ]
    
    success_count = 0
    fail_count = 0
    
    # 使用线程池并发处理
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        future_to_row = {
            executor.submit(process_single_row, task): task[0]
            for task in row_tasks
        }
        
        # 使用 tqdm 显示进度
        with tqdm(total=len(row_tasks), desc=f"Rows in {filename}", unit="row") as pbar:
            # 收集结果
            results = {}
            for future in as_completed(future_to_row):
                try:
                    row_idx, processed_row, success, failed = future.result()
                    results[row_idx] = processed_row
                    if success:
                        success_count += 1
                    if failed:
                        fail_count += 1
                except Exception as e:
                    row_idx = future_to_row[future]
                    log_error(filename, row_idx + 1, f"Thread execution error: {e}")
                    # 确保失败的行也被记录到结果中（保持原始状态或标记为错误）
                    if row_idx not in results:
                        # 使用原始行，但标记为错误
                        original_row = rows[row_idx + 1].copy() if row_idx + 1 < len(rows) else [""] * 6
                        while len(original_row) < 6:
                            original_row.append("")
                        if len(original_row) > 3:
                            original_row[3] = "[THREAD_ERROR]"
                        results[row_idx] = original_row
                    fail_count += 1
                finally:
                    pbar.update(1)
    
    # 按原始顺序重新组装 rows（保持顺序）
    # 确保所有行都被处理，缺失的用原始行填充
    sorted_indices = sorted(results.keys())
    processed_rows = []
    for i in range(len(data_rows)):
        if i in results:
            processed_rows.append(results[i])
        else:
            # 如果某行没有被处理（不应该发生，但为了安全）
            original_row = rows[i + 1].copy() if i + 1 < len(rows) else [""] * 6
            while len(original_row) < 6:
                original_row.append("")
            processed_rows.append(original_row)
    rows[1:] = processed_rows
    
    # 计算准确率统计（无论输出格式如何都计算）
    accuracy_stats = []
    
    def is_correct_result(result_str):
        """判断比较结果是否为'正确'（更精确的判断逻辑）"""
        if not result_str:
            return False
        result = str(result_str).strip()
        result_lower = result.lower()
        
        # 检查"正确"相关关键词（排除"不正确"）
        if "正确" in result:
            # 如果包含"不正确"这个完整词，则不是正确
            if "不正确" in result:
                return False
            # 如果"不"在"正确"之前，则不是正确
            idx_bu = result.find("不")
            idx_zhengque = result.find("正确")
            if idx_bu >= 0 and idx_zhengque >= 0 and idx_bu < idx_zhengque:
                return False
            return True
        
        # 检查"一致"相关关键词（排除"不一致"）
        if "一致" in result:
            # 如果包含"不一致"这个完整词，则不是正确
            if "不一致" in result:
                return False
            return True
        
        # 检查英文"same"（排除"not same"）
        if "same" in result_lower:
            # 如果包含"not same"这个完整短语，则不是正确
            if "not same" in result_lower:
                return False
            return True
        
        return False
    
    def is_error_result(result_str):
        """判断比较结果是否为'错误'（更精确的判断逻辑）"""
        if not result_str:
            return False
        result = str(result_str).strip()
        result_lower = result.lower()
        
        # 检查"错误"相关关键词
        if "错误" in result or result_lower == "错误":
            return True
        
        # 检查"不一致"、"不同"
        if "不一致" in result or "不同" in result:
            return True
        
        # 检查英文"different"
        if "different" in result_lower:
            return True
        
        # 检查"不正确"
        if "不正确" in result:
            return True
        
        return False
    
    # 统计辅助小结一致性比较结果（第5列，索引4：评估结果）
    if len(header) > 4:
        correct_count = 0
        error_count = 0
        for row in rows[1:]:
            if len(row) > 4:
                result = str(row[4]).strip()  # 第5列：评估结果
                # 排除空值和错误信息
                if result and result != "API Error" and not result.startswith("JSON Parse Error") and not result.startswith("Compare Error"):
                    if is_correct_result(result):
                        correct_count += 1
                    elif is_error_result(result):
                        error_count += 1
        total = correct_count + error_count
        accuracy = correct_count / total if total > 0 else 0.0
        accuracy_stats.append({
            "比较类型": "辅助小结一致性比较（第3列 vs 第4列）",
            "正确的记录数": correct_count,
            "错误的记录数": error_count,
            "总记录数": total,
            "准确率": f"{accuracy:.2%}" if total > 0 else "N/A"
        })
            
    # Write back to a new file: *_result_{systemtime}.xlsx or .csv
    process_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result_path = ""
    try:
        # 确保结果目录存在
        if not os.path.exists(RESULT_DIR):
            os.makedirs(RESULT_DIR, exist_ok=True)
        
        # 获取原始文件名（不含路径）
        original_filename = os.path.basename(file_path)
        base, ext = os.path.splitext(original_filename)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 根据配置的输出格式选择保存方式
        use_excel = (OUTPUT_FORMAT == "excel" and PANDAS_AVAILABLE and EXCEL_AVAILABLE)
        
        if use_excel:
            result_filename = f"{base}_result_{ts}.xlsx"
            result_path = os.path.join(RESULT_DIR, result_filename)
            
            # 将数据转换为DataFrame
            # 确保列名数量与数据列数匹配
            max_cols = max(len(row) for row in rows[1:]) if len(rows) > 1 else len(header)
            if len(header) < max_cols:
                header_extended = header + [""] * (max_cols - len(header))
            else:
                header_extended = header[:max_cols]
            df_data = pd.DataFrame(rows[1:], columns=header_extended)
            
            # 创建Excel写入器
            with pd.ExcelWriter(result_path, engine='openpyxl') as writer:
                # 写入主数据sheet
                df_data.to_excel(writer, sheet_name='处理结果', index=False)
                
                # 如果有准确率统计，写入统计sheet
                if accuracy_stats:
                    df_stats = pd.DataFrame(accuracy_stats)
                    df_stats.to_excel(writer, sheet_name='准确率统计', index=False)
            
            print(f"Saved {os.path.basename(result_path)}: {success_count} success, {fail_count} failed.")
            if accuracy_stats:
                print("准确率统计:")
                for stat in accuracy_stats:
                    print(f"  {stat['比较类型']}: {stat['准确率']} ({stat['正确的记录数']}/{stat['总记录数']})")
        else:
            # 使用CSV格式输出（默认或pandas/openpyxl不可用）
            result_filename = f"{base}_result_{ts}{ext}"
            result_path = os.path.join(RESULT_DIR, result_filename)
            with open(result_path, 'w', encoding=encoding, newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
                
                # 如果有准确率统计，在CSV文件末尾添加统计信息
                if accuracy_stats:
                    # 添加空行作为分隔
                    writer.writerow([])
                    writer.writerow(["准确率统计"])
                    writer.writerow(["比较类型", "正确的记录数", "错误的记录数", "总记录数", "准确率"])
                    
                    # 添加统计数据行
                    for stat in accuracy_stats:
                        writer.writerow([
                            stat['比较类型'],
                            stat['正确的记录数'],
                            stat['错误的记录数'],
                            stat['总记录数'],
                            stat['准确率']
                        ])
            
            print(f"Saved {os.path.basename(result_path)}: {success_count} success, {fail_count} failed.")
            # 如果配置为excel但依赖不可用，给出提示
            if OUTPUT_FORMAT == "excel":
                if not PANDAS_AVAILABLE:
                    print("提示: 配置为excel格式，但pandas未安装，已回退到CSV格式。如需Excel格式输出，请安装: pip install pandas openpyxl")
                elif not EXCEL_AVAILABLE:
                    print("提示: 配置为excel格式，但openpyxl未安装，已回退到CSV格式。如需Excel格式输出，请安装: pip install openpyxl")
            if accuracy_stats:
                print("准确率统计:")
                for stat in accuracy_stats:
                    print(f"  {stat['比较类型']}: {stat['准确率']} ({stat['正确的记录数']}/{stat['总记录数']})")
    except Exception as e:
        print(f"Failed to save result file for {filename}: {e}")
        import traceback
        traceback.print_exc()
        result_path = ""  # 保存失败时，result_path为空
    
    # 记录处理结果到summary.log
    if result_path:
        # 构建提示词文件名列表（用逗号分隔）
        prompt_files = []
        if PROMPT_FILE_NAME:
            prompt_files.append(PROMPT_FILE_NAME)
        if COMPARE_PROMPT_FILE_NAME:
            prompt_files.append(COMPARE_PROMPT_FILE_NAME)
        prompt_filename_str = ", ".join(prompt_files) if prompt_files else "无"
        
        log_summary(
            process_time=process_time,
            csv_filename=os.path.basename(file_path),
            output_filename=os.path.basename(result_path),
            prompt_filename=prompt_filename_str,
            accuracy_stats=accuracy_stats,
            sample_size=actual_sample_size if SAMPLE_SIZE > 0 else 0,
            total_rows=total_rows_count,
            main_model=MODEL,
            main_temperature=TEMPERATURE,
            main_top_p=TOP_P,
            compare_model=COMPARE_MODEL,
            compare_temperature=COMPARE_TEMPERATURE,
            compare_top_p=COMPARE_TOP_P
        )
        
    return success_count, fail_count

def main():
    # 加载配置文件
    try:
        load_config()
    except Exception as e:
        print(f"错误: 加载配置文件失败: {e}")
        return
    
    print("Starting Batch Summary Generator...")
    print(f"主模型鉴权: {'启用' if MAIN_ENABLE_AUTH else '禁用'}")
    if MAIN_ENABLE_AUTH:
        print(f"  自行计算authorization: {'是' if MAIN_CALCULATE_AUTH else '否（直接使用配置值）'}")
    print(f"比较模型鉴权: {'启用' if COMPARE_ENABLE_AUTH else '禁用'}")
    if COMPARE_ENABLE_AUTH:
        print(f"  自行计算authorization: {'是' if COMPARE_CALCULATE_AUTH else '否（直接使用配置值）'}")
    
    # 1. Load Prompt
    if not os.path.exists(PROMPT_FILE):
        print(f"Error: Prompt file not found at {PROMPT_FILE}")
        return
        
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    # 1.1 Load compare Prompt
    if not os.path.exists(COMPARE_PROMPT_FILE):
        print(f"Warning: Compare prompt file not found at {COMPARE_PROMPT_FILE}, compare step will be skipped.")
        compare_template = ""
    else:
        with open(COMPARE_PROMPT_FILE, 'r', encoding='utf-8') as f:
            compare_template = f.read()
        
    # 2. Get CSV file(s) to process
    if CSV_FILE_NAME and CSV_FILE_NAME.strip():
        # 处理指定文件
        csv_file_path = os.path.join(CSV_DIR, CSV_FILE_NAME.strip())
        if not os.path.exists(csv_file_path):
            print(f"Error: Specified CSV file not found: {csv_file_path}")
            print(f"Please check if the file exists in {CSV_DIR}")
            return
        csv_files = [csv_file_path]
        print(f"Processing specified file: {CSV_FILE_NAME}")
    else:
        # 扫描目录下所有CSV文件（兼容旧逻辑）
        csv_files = glob.glob(os.path.join(CSV_DIR, "*.csv"))
        # 排除结果文件（包含_result_的文件）
        csv_files = [f for f in csv_files if "_result_" not in os.path.basename(f)]
        if not csv_files:
            print(f"No CSV files found in {CSV_DIR}")
            print(f"Tip: You can set CSV_FILE_NAME in the configuration to process a specific file.")
            return
        print(f"Found {len(csv_files)} CSV files in directory (processing all).")
        
    total_files = len(csv_files)
    total_success = 0
    total_fail = 0
    start_time = time.time()
    
    # 3. Process each file
    for file_path in csv_files:
        s, f = process_file(file_path, prompt_template, compare_template)
        total_success += s
        total_fail += f
        
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "="*30)
    print("处理完成")
    print(f"总文件数: {total_files}")
    print(f"已处理总行数: {total_success + total_fail}")
    print(f"成功: {total_success}")
    print(f"失败: {total_fail}")
    print(f"耗时: {duration:.2f} 秒")
    print(f"日志文件: {LOG_FILE}")
    print("="*30)

if __name__ == "__main__":
    main()
