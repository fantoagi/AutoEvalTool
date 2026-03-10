"""
数据库模块 - SQLite历史记录管理
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional


DB_FILE = os.path.join(os.path.dirname(__file__), "eval_history.db")


def init_database():
    """初始化数据库，创建表结构"""
    try:
        # 添加超时设置，避免数据库锁定导致卡住
        conn = sqlite3.connect(DB_FILE, timeout=5.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS eval_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                file TEXT NOT NULL,
                columns TEXT NOT NULL,
                model TEXT NOT NULL,
                records INTEGER NOT NULL,
                accuracy REAL,
                prompt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as e:
        # 数据库被锁定或其他操作错误
        print(f"[警告] 数据库初始化失败: {e}")
        print(f"[提示] 如果数据库文件被锁定，请关闭其他可能使用该文件的程序")
    except Exception as e:
        print(f"[警告] 数据库初始化出错: {e}")


def save_eval_history(
    file: str,
    columns: str,
    model: str,
    records: int,
    accuracy: Optional[float],
    prompt: str
):
    """
    保存评估历史记录
    
    Args:
        file: 文件名
        columns: 列映射信息（格式：Ref: [列A] vs Eval: [列B]）
        model: 模型名称
        records: 总记录数
        accuracy: 准确率（0-1之间的小数）
        prompt: 使用的提示词
    """
    init_database()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO eval_history (time, file, columns, model, records, accuracy, prompt)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (time_str, file, columns, model, records, accuracy, prompt))
    
    conn.commit()
    conn.close()


def get_eval_history(limit: int = 50) -> List[Dict]:
    """
    获取评估历史记录
    
    Args:
        limit: 返回记录数限制
    
    Returns:
        list: 历史记录列表，每个元素是一个字典
    """
    init_database()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT time, file, columns, model, records, accuracy, prompt
        FROM eval_history
        ORDER BY created_at DESC
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "time": row[0],
            "file": row[1],
            "columns": row[2],
            "model": row[3],
            "records": row[4],
            "accuracy": row[5],
            "prompt": row[6]
        })
    
    return history
