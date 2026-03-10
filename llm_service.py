"""
LLM服务模块 - 处理LLM API调用、鉴权与日志记录
参考 batch_summary_generator.py 中的比较模型配置和鉴权处理逻辑
"""
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
import hmac
import hashlib
import base64
import os
import sys
import threading


def _get_log_dir():
    """获取日志目录：打包为 exe 时用 exe 所在目录，否则用脚本所在目录"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# 日志文件路径（exe 运行时写入 exe 同目录，脚本运行时写入脚本同目录）
LOG_FILE = os.path.join(_get_log_dir(), "process.log")

# 日志写入锁，确保多线程环境下日志写入的线程安全
_log_lock = threading.Lock()


def log_llm_detail(message: str) -> None:
    """记录LLM相关日志（可供其他模块调用，便于问题定位）"""
    _log_llm_detail(message)


def _log_llm_detail(message: str) -> None:
    """记录LLM请求/响应明细到日志文件（线程安全）。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _log_lock:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            # 避免因为日志写入失败影响主流程
            pass


def encode_payload_string(payload_str):
    """将payload字符串编码为Base64并URL编码"""
    payload_bytes = payload_str.encode('utf-8')
    base64_encoded = base64.b64encode(payload_bytes).decode('utf-8')
    url_encoded = urllib.parse.quote(base64_encoded)
    return url_encoded


def generate_auth_headers(auth_config):
    """
    生成鉴权headers（支持HMAC-SHA1签名）
    
    Args:
        auth_config: 鉴权配置字典，包含以下字段：
            - enable_auth: bool, 是否启用鉴权
            - calculate_auth: bool, 是否自行计算authorization
            - authorization: str, 直接使用的authorization值
            - app_key: str, AppKey
            - app_secret: str, AppSecret
            - source: str, Source（应用ID）
            - org_id, org_name, full_org_name, oa_code, user_name: 用户信息
    
    Returns:
        dict: 鉴权headers字典
    """
    if not auth_config.get('enable_auth', False):
        return {}
    
    # 如果不需要自行计算，直接使用配置的authorization值
    if not auth_config.get('calculate_auth', True):
        authorization = auth_config.get('authorization', '')
        if authorization:
            return {'Authorization': authorization}
        else:
            return {}
    
    # 自行计算authorization
    org_id = auth_config.get('org_id', '')
    org_name = auth_config.get('org_name', '')
    full_org_name = auth_config.get('full_org_name', '')
    oa_code = auth_config.get('oa_code', '')
    user_name = auth_config.get('user_name', '')
    
    # 生成payload
    if org_id or org_name or full_org_name or oa_code or user_name:
        payload_dict = {
            "orgId": org_id,
            "orgName": org_name,
            "fullOrgName": full_org_name,
            "oaCode": oa_code,
            "userName": user_name
        }
        payload_str = json.dumps(payload_dict, ensure_ascii=False)
    else:
        payload_str = "{}"
    
    # 编码payload
    custom_payload = encode_payload_string(payload_str)
    
    # 获取当前GMT时间
    try:
        now = datetime.now(datetime.UTC)
    except AttributeError:
        now = datetime.now(timezone.utc)
    date_time = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    # 生成签名字符串
    source = auth_config.get('source', '')
    sign_str = f"x-date: {date_time}\nsource: {source}\nx-custom-payload: {custom_payload}"
    
    # HMAC-SHA1签名
    app_secret = auth_config.get('app_secret', '')
    signature = hmac.new(
        app_secret.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha1
    ).digest()
    
    # Base64编码签名
    signature_base64 = base64.b64encode(signature).decode('utf-8')
    
    # 生成Authorization header
    app_key = auth_config.get('app_key', '')
    auth_str = f'hmac username="{app_key}", algorithm="hmac-sha1", headers="x-date source x-custom-payload", signature="{signature_base64}"'
    
    # 返回headers
    headers = {
        'Source': source,
        'X-Date': date_time,
        'Authorization': auth_str,
        'X-Custom-Payload': custom_payload
    }
    
    return headers


def _mask_api_key(api_key: str) -> str:
    """脱敏API Key，仅显示前后各2位"""
    if not api_key or len(api_key) <= 4:
        return "****"
    return f"{api_key[:2]}...{api_key[-2:]}"


def call_llm(prompt, api_base_url, api_key, model_name, temperature=0.0, max_tokens=512, auth_config=None, task_id=None):
    """
    调用LLM API
    
    Args:
        prompt: 提示词
        api_base_url: API基础URL
        api_key: API密钥
        model_name: 模型名称
        temperature: 温度参数（默认0.0）
        max_tokens: 最大token数（默认512）
        auth_config: 鉴权配置字典（可选）
        task_id: 任务标识（如行号），用于日志关联定位
    
    Returns:
        str: LLM返回的文本内容
    
    Raises:
        Exception: API调用失败时抛出异常
    """
    tid = f"[Task-{task_id}] " if task_id is not None else ""
    # 构建headers
    headers = {"Content-Type": "application/json"}

    # 处理鉴权
    if auth_config and auth_config.get("enable_auth", False):
        auth_headers = generate_auth_headers(auth_config)
        headers.update(auth_headers)
    else:
        # 使用Bearer Token
        headers["Authorization"] = f"Bearer {api_key}"

    # 构建请求数据
    data = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # 记录请求日志（脱敏API Key，便于问题定位）
    try:
        _log_llm_detail(f"{tid}===== LLM 请求开始 =====")
        _log_llm_detail(f"{tid}URL: {api_base_url}")
        _log_llm_detail(f"{tid}Model: {model_name}, Temperature: {temperature}, MaxTokens: {max_tokens}")
        _log_llm_detail(f"{tid}API Key: {_mask_api_key(api_key)}")
        _log_llm_detail(f"{tid}Prompt 长度: {len(prompt)} 字符")
        _log_llm_detail(f"{tid}Request Body: {json.dumps(data, ensure_ascii=False)}")
    except Exception:
        pass

    try:
        req = urllib.request.Request(
            api_base_url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=60) as res:
            raw = res.read().decode("utf-8")

            # 记录原始响应（便于定位解析问题）
            try:
                _log_llm_detail(f"{tid}===== LLM 原始响应 =====")
                _log_llm_detail(f"{tid}Raw Response (长度 {len(raw)}): {raw[:2000]}{'...(截断)' if len(raw) > 2000 else ''}")
            except Exception:
                pass

            try:
                response = json.loads(raw)
            except json.JSONDecodeError as e:
                try:
                    _log_llm_detail(f"{tid}[JSON 解析失败] {e}，原始响应前500字符: {raw[:500]}")
                except Exception:
                    pass
                raise Exception(f"API 响应非合法 JSON: {e}")

            # 兼容多种 API 响应格式
            content = None
            if isinstance(response, dict):
                # OpenAI 格式: choices[0].message.content
                choices = response.get("choices")
                if choices and len(choices) > 0:
                    msg = choices[0] if isinstance(choices[0], dict) else None
                    if msg:
                        content = msg.get("message", {}).get("content") if isinstance(msg.get("message"), dict) else msg.get("content")
                # DashScope/阿里云 格式: output.text
                if content is None:
                    output = response.get("output")
                    if isinstance(output, dict):
                        content = output.get("text")
                # 其他格式: data.text / result
                if content is None:
                    content = response.get("data", {}).get("text") if isinstance(response.get("data"), dict) else response.get("result")

            if content is None:
                try:
                    _log_llm_detail(f"{tid}[解析失败] 无法从响应中提取 content，响应结构: {json.dumps(response, ensure_ascii=False)[:500]}")
                except Exception:
                    pass
                raise Exception(f"API 响应格式异常: 无法提取 content，请查看 process.log 中的原始响应")

            # 记录解析后的内容
            try:
                _log_llm_detail(f"{tid}提取的 Content: {str(content)[:500]}{'...(截断)' if len(str(content)) > 500 else ''}")
                _log_llm_detail(f"{tid}===== LLM 响应结束 =====")
            except Exception:
                pass

            return content
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            _log_llm_detail(f"{tid}[HTTP Error {e.code}] {err_body[:1000]}")
        except Exception:
            pass
        raise Exception(f"HTTP Error {e.code}: {err_body}")
    except Exception as e:
        try:
            _log_llm_detail(f"{tid}[API Error] {type(e).__name__}: {e}")
        except Exception:
            pass
        raise Exception(f"API Error: {e}")
