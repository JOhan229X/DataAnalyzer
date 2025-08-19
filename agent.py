# agent.py

import streamlit as st
from datetime import datetime, timedelta

# 导入重构后的模块
from database import get_watchlist, get_unread_alerts, save_alert
from intelligence import search_news_links, browse_article_text, get_ai_structured_summary

def run_monitoring_agent():
    """
    后台监控Agent的主函数。
    它会遍历数据库中的watchlist，为每家公司搜索最新信息，并创建警报。
    """
    watchlist = get_watchlist()
    if not watchlist:
        st.toast("监控列表为空，无需运行。", icon="ℹ️")
        return

    st.toast(f"后台监控Agent启动，正在监视 {len(watchlist)} 家公司...", icon="🤖")

    # 获取已存在的警报URL，避免重复处理
    existing_alerts = get_unread_alerts()
    existing_urls = {alert['source_url'] for alert in existing_alerts}

    for company_name in watchlist:
        # 使用 status 让UI反馈更友好
        with st.status(f"正在为 {company_name} 搜索新闻...", state="running") as status:
            
            # 1. 搜索新闻
            news_items = search_news_links(company_name, num_articles=1) # 每次只检查最新的1篇
            if not news_items:
                status.update(label=f"未找到 {company_name} 的新文章。", state="complete", expanded=False)
                continue

            latest_news = news_items[0]
            news_url = latest_news.get("url")
            news_title = latest_news.get("title", "无标题")

            if not news_url or news_url in existing_urls:
                status.update(label=f"跳过已处理或无效的文章: {news_title}", state="complete", expanded=False)
                continue

            # 2. 读取文章内容
            status.update(label=f"发现新文章: '{news_title[:30]}...'。正在读取...", state="running")
            full_text = browse_article_text(news_url)
            if not full_text:
                status.update(label=f"无法读取文章内容: {news_title}", state="error", expanded=False)
                continue

            # 3. AI分析
            status.update(label=f"正在调用AI分析文章...", state="running")
            ai_insight = get_ai_structured_summary(full_text, company_name)

            if ai_insight:
                # 4. 创建并保存警报
                alert_text = f"**{ai_insight.event_type}**: {ai_insight.summary} (情绪: {ai_insight.sentiment})"
                save_alert(company_name, alert_text, news_url, news_title)
                st.toast(f"为 {company_name} 创建了新警报!", icon="🔔")
                status.update(label=f"为 {company_name} 创建新警报成功!", state="complete")
            else:
                status.update(label=f"AI未能分析文章: {news_title}", state="error")
    
    st.success("后台监控Agent运行完毕。")

if __name__ == "__main__":
    # 此部分允许未来通过命令行或定时任务（cron job）运行此脚本
    print("正在以脚本模式运行后台监控Agent...")
    run_monitoring_agent()
    print("运行结束。")