# app.py (对话式Agent版本)
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import os
import pandas as pd
from typing import Dict
from langchain.memory import ConversationBufferMemory
# --- 导入我们所有的后台模块和工具 ---
from engine import (
    generate_cash_flow_forecast,
    calculate_runway_and_score,
    analyze_funding_urgency
)
from models import FinancialInput, B2BContract, ScenarioInput
from database import (
    create_company_table, setup_monitoring_tables, 
    add_to_watchlist, remove_from_watchlist, get_watchlist, get_unread_alerts, mark_alert_as_read
)
from intelligence import search_news_links, browse_article_text, get_ai_structured_summary
from mock_data_provider import get_mock_company_data
from agent_brain import initialize_agent, get_agent_response


def display_alerts():
    """在侧边栏显示未读的监控警报"""
    st.sidebar.title("🔔 监控警报中心")

    unread_alerts = get_unread_alerts()

    if not unread_alerts:
        st.sidebar.info("目前没有新的警报。")
        return

    st.sidebar.success(f"您有 {len(unread_alerts)} 条未读警报！")

    # 为了让每个警报都能独立展开/折叠，我们用 expander
    for alert in unread_alerts:
        with st.sidebar.expander(f"**{alert['company_name']}**: {alert['news_title'][:30]}"):
            st.markdown(alert['alert_text'])
            st.markdown(f"[阅读原文]({alert['source_url']})")

            # 创建一个唯一的key，防止所有按钮都互相影响
            button_key = f"read_{alert['id']}"
            if st.button("标记为已读", key=button_key):
                mark_alert_as_read(alert['id'])
                st.rerun() # 立即刷新界面，让已读的警报消失
# =============================================================================
# Streamlit UI (现在是对话式界面)
# =============================================================================

def main():
    st.set_page_config(page_title="推理分析Agent", layout="wide")

    # 初始化数据库表
    create_company_table()
    setup_monitoring_tables()
    
    # 初始化Agent的核心组件 (LLM和Prompt)
    initialize_agent()

    display_alerts()
    # 为当前会话初始化记忆模块
    if "memory" not in st.session_state:
        st.session_state.memory = ConversationBufferMemory(memory_key="chat_history")

    st.title(" CF   Agent ")
    st.caption("Make the analysis more accurate and faster")

    # 初始化聊天记录
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "您好！我是CF Bot，您的AI分析师。有什么可以帮您？"}]

    # 显示历史消息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 接收用户输入
    if prompt := st.chat_input("例如: 月之暗面最近有什么新闻?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("InsightBot正在深度分析中..."):
                # ✅ 修正：在这里传入当前会话的记忆模块作为第二个参数
                response = get_agent_response(prompt, st.session_state.memory)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.markdown(response)


if __name__ == "__main__":
    main()