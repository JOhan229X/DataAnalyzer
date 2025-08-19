# database.py

import json
import sqlite3
from models import CompetitiveInput, FinancialInput

DB_FILE = "companies_data.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False) # check_same_thread=False for Streamlit
    conn.row_factory = sqlite3.Row
    return conn

# --- 公司数据存储相关 ---

def create_company_table():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                competitive_data TEXT,
                financial_data TEXT
            )
        ''')

def save_company_data(company_name: str, competitive_input: CompetitiveInput, financial_input: FinancialInput):
    with get_db_connection() as conn:
        competitive_json = competitive_input.model_dump_json()
        financial_json = financial_input.model_dump_json()
        conn.execute('''
            INSERT OR REPLACE INTO companies (name, competitive_data, financial_data)
            VALUES (?, ?, ?)
        ''', (company_name, competitive_json, financial_json))

def get_all_company_names() -> list:
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT name FROM companies ORDER BY name")
        return [row['name'] for row in cursor.fetchall()]

def load_company_data(company_name: str) -> tuple:
    with get_db_connection() as conn:
        data = conn.execute("SELECT * FROM companies WHERE name = ?", (company_name,)).fetchone()
    
    if data:
        competitive_data = json.loads(data['competitive_data'])
        financial_data = json.loads(data['financial_data'])
        return competitive_data, financial_data
    return None, None

def delete_company_data(company_name: str):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM companies WHERE name = ?", (company_name,))

# --- 后台监控Agent相关 ---

def setup_monitoring_tables():
    """创建用于监控Agent的表"""
    with get_db_connection() as conn:
        # 监视列表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY,
                company_name TEXT NOT NULL UNIQUE
            )
        ''')
        # 警报信息
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY,
                company_name TEXT NOT NULL,
                alert_text TEXT NOT NULL,
                source_url TEXT UNIQUE,
                news_title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER DEFAULT 0
            )
        ''')

def get_watchlist() -> list:
    """获取所有在监视列表中的公司名称"""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT company_name FROM watchlist ORDER BY company_name")
        return [row['company_name'] for row in cursor.fetchall()]

def add_to_watchlist(company_name: str):
    """将公司添加到监视列表"""
    with get_db_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO watchlist (company_name) VALUES (?)", (company_name,))

def remove_from_watchlist(company_name: str):
    """从监视列表移除公司"""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM watchlist WHERE company_name = ?", (company_name,))

def save_alert(company_name: str, alert_text: str, source_url: str, news_title: str):
    """保存新的警报"""
    with get_db_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO alerts (company_name, alert_text, source_url, news_title)
            VALUES (?, ?, ?, ?)
        """, (company_name, alert_text, source_url, news_title))

def get_unread_alerts() -> list:
    """获取所有未读的警报"""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT * FROM alerts WHERE is_read = 0 ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def mark_alert_as_read(alert_id: int):
    """将警报标记为已读"""
    with get_db_connection() as conn:
        conn.execute("UPDATE alerts SET is_read = 1 WHERE id = ?", (alert_id,))