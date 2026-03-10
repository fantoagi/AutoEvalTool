"""
工具函数模块 - JSON解析、准确率计算等
"""
import json
import re
from typing import Dict, Optional, Tuple

# 延迟导入，避免循环依赖
def _get_logger():
    try:
        from llm_service import log_llm_detail
        return log_llm_detail
    except ImportError:
        return lambda msg: None


def extract_json_from_text(text: str) -> Optional[Dict]:
    """
    从文本中提取JSON对象（鲁棒性处理）
    支持从包含markdown标记或其他文本的响应中提取 {...} JSON对象
    
    Args:
        text: 可能包含JSON的文本
    
    Returns:
        dict: 解析后的JSON字典，如果解析失败返回None
    """
    if not text:
        return None
    
    # 首先尝试直接解析
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # 尝试提取markdown代码块中的JSON
    json_patterns = [
        r'```json\s*(\{.*?\})\s*```',  # ```json {...} ```
        r'```\s*(\{.*?\})\s*```',      # ``` {...} ```
        r'(\{.*\})',                    # 直接提取 {...}
    ]
    
    for pattern in json_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue
    
    # 如果所有方法都失败，尝试找到第一个 { 到最后一个 } 之间的内容
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace >= 0 and last_brace > first_brace:
        json_str = text[first_brace:last_brace + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    return None


def parse_llm_evaluation_response(response_text: str, task_id=None) -> Tuple[str, str]:
    """
    解析LLM评估响应，提取result和reason
    
    Args:
        response_text: LLM返回的文本
        task_id: 任务标识（如行号），用于日志关联
    
    Returns:
        tuple: (result, reason) - 如果解析失败，result为"Error"，reason为错误信息
    """
    tid = f"[Task-{task_id}] " if task_id is not None else ""
    _log = _get_logger()

    json_data = extract_json_from_text(response_text)
    
    if json_data is None:
        try:
            _log(f"{tid}[JSON解析失败] 无法从响应中提取JSON，原始内容前300字符: {str(response_text)[:300] if response_text else 'None'}")
        except Exception:
            pass
        return "Error", "JSON解析失败"
    
    # 尝试多种可能的键名（不区分大小写）
    result = None
    reason = None
    
    # 查找result字段（支持多种命名）
    for key in ['result', '评估结果', 'evaluation_result', 'judgment', '判断']:
        if key in json_data:
            result = str(json_data[key]).strip()
            break
    
    # 查找reason字段（支持多种命名）
    for key in ['reason', '原因', '评估理由', 'evaluation_reason', 'explanation', '说明']:
        if key in json_data:
            reason = str(json_data[key]).strip()
            break
    
    # 如果找不到标准字段，尝试获取所有值
    if result is None or reason is None:
        values = list(json_data.values())
        if len(values) >= 2:
            if result is None:
                result = str(values[0]).strip()
            if reason is None:
                reason = str(values[1]).strip()
        elif len(values) == 1:
            if result is None:
                result = str(values[0]).strip()
            reason = ""
    
    if result is None:
        result = "Error"
    if reason is None:
        reason = "无法提取评估原因"

    # 解析异常时记录日志，便于定位
    if result == "Error" or "无法提取" in str(reason):
        try:
            _log(f"{tid}[解析异常] result={result}, reason={reason}, 原始响应前200字符: {str(response_text)[:200] if response_text else 'None'}")
        except Exception:
            pass

    return result, reason


def is_correct_result(result_str: str) -> bool:
    """
    判断评估结果是否为"正确"（不区分大小写）
    
    Args:
        result_str: 评估结果字符串
    
    Returns:
        bool: 如果结果为"正确"返回True，否则返回False
    """
    if not result_str:
        return False
    
    result = str(result_str).strip()
    result_lower = result.lower()
    
    # 检查"正确"相关关键词（排除"不正确"）
    if "正确" in result:
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
        if "不一致" in result:
            return False
        return True
    
    # 检查英文"correct"或"same"（排除"not correct"、"not same"）
    if result_lower in ["correct", "same", "match", "true", "yes"]:
        return True
    if "not correct" in result_lower or "not same" in result_lower:
        return False
    
    return False


def is_incorrect_result(result_str: str) -> bool:
    """
    判断评估结果是否为"错误"（不区分大小写）
    
    Args:
        result_str: 评估结果字符串
    
    Returns:
        bool: 如果结果为"错误"返回True，否则返回False
    """
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
    
    # 检查"不正确"
    if "不正确" in result:
        return True
    
    # 检查英文"incorrect"、"different"、"wrong"
    if result_lower in ["incorrect", "different", "wrong", "false", "no", "mismatch"]:
        return True
    
    return False


# 导入pandas用于calculate_accuracy函数
try:
    import pandas as pd
except ImportError:
    pd = None


def calculate_accuracy(df, result_column: str) -> Dict:
    """
    计算准确率统计
    
    Args:
        df: pandas DataFrame
        result_column: 结果列名
    
    Returns:
        dict: 包含准确率统计信息的字典
    """
    if pd is None:
        raise ImportError("pandas is required for calculate_accuracy function")
    
    if result_column not in df.columns:
        return {
            "correct_count": 0,
            "incorrect_count": 0,
            "error_count": 0,
            "total_valid": 0,
            "accuracy": 0.0
        }
    
    correct_count = 0
    incorrect_count = 0
    error_count = 0
    
    for _, row in df.iterrows():
        result = str(row[result_column]).strip() if pd.notna(row[result_column]) else ""
        
        # 跳过空值和错误标记
        if not result or result == "Error" or result.startswith("JSON") or result.startswith("API"):
            if result:
                error_count += 1
            continue
        
        if is_correct_result(result):
            correct_count += 1
        elif is_incorrect_result(result):
            incorrect_count += 1
    
    total_valid = correct_count + incorrect_count
    accuracy = correct_count / total_valid if total_valid > 0 else 0.0
    
    return {
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "error_count": error_count,
        "total_valid": total_valid,
        "accuracy": accuracy
    }
