# intelligence.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import quote_plus
from typing import Optional, List, Dict
from models import AIInsight
import trafilatura
import logging

# --- 配置 ---
# 从环境变量安全加载API密钥
NEWS_API_KEY = st.secrets.get("NEWS_API_KEY", os.getenv("NEWS_API_KEY"))
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
# --- 内部函数 ---
def _search_newsapi(company_name: str) -> List[Dict]:
    """私有函数：通过NewsAPI进行搜索"""
    if not NEWS_API_KEY:
        st.warning("NewsAPI 密钥未设置，跳过此情报源。")
        return []

    query = f'"{company_name}"'
    url = f"https://newsapi.org/v2/everything?q={quote_plus(query)}&language=zh&sortBy=publishedAt&pageSize=20"
    headers = {"Authorization": f"Bearer {NEWS_API_KEY}"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("articles", []) if data.get("status") == "ok" else []
    except requests.exceptions.RequestException as e:
        st.warning(f"通过 NewsAPI 搜索失败: {e}")
        return []

def _search_bing_rss(company_name: str) -> List[Dict]:
    """私有函数：通过Bing新闻RSS进行搜索作为备用"""
    search_query = quote_plus(f'"{company_name}"')
    url = f"https://www.bing.com/news/search?q={search_query}&format=rss"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        articles = []
        for item in soup.find_all('item'):
            articles.append({
                "title": item.find('title').text if item.find('title') else "",
                "url": item.find('link').text if item.find('link') else "",
                "description": item.find('description').text if item.find('description') else "",
            })
        return articles
    except requests.exceptions.RequestException as e:
        st.warning(f"通过 Bing News RSS 备用源搜索失败: {e}")
        return []

# --- 外部调用函数 ---

@st.cache_data(ttl=3600)  # 缓存1小时
def search_news_links(company_name: str, num_articles: int = 5) -> List[Dict]:
    """
    多源情报获取与去重、过滤
    """
    all_articles = []
    seen_urls = set()

    # 来源1: NewsAPI
    newsapi_articles = _search_newsapi(company_name)
    
    # 来源2: Bing News RSS (作为补充或备用)
    bing_articles = _search_bing_rss(company_name)
    
    # 合并与去重
    for article_list in [newsapi_articles, bing_articles]:
        for article in article_list:
            url = article.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_articles.append(article)

    # 过滤不相关的文章
    relevant_articles = []
    for article in all_articles:
        title = article.get("title", "")
        description = article.get("description", "")
        if company_name in title or company_name in description:
            relevant_articles.append({"title": title, "url": article["url"]})
            
    if not relevant_articles:
        st.warning(f"未能检索到关于 “{company_name}” 的强相关新闻。")

    return relevant_articles[:num_articles]

@st.cache_data(ttl=86400) # 缓存1天
def browse_article_text(url: str) -> str:
    """用 Jina Reader 读取网页正文，带普通requests作为降级方案"""
    try:
        reader_url = f"https://r.jina.ai/{url}"
        resp = requests.get(reader_url, timeout=20)
        resp.raise_for_status()
        content = ""
        # Jina Reader 可能直接返回文本，也可能返回JSON
        if resp.text.strip().startswith("{"):
             content = resp.json().get("data", {}).get("content", "")
        else:
            content = resp.text
        if len(content) > 100: # 简单判断内容是否有效
             return content
    except Exception as e:
        logging.warning(f"[Jina Reader 失败] URL: {url}, Error: {e}")


    # 降级方案: 普通爬虫
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        paragraphs = soup.find_all('p')
        paras = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 30]
        if paras:
            return "\n".join(paras)
    except Exception as e:
        # --- MODIFIED ---
        logging.warning(f"[BeautifulSoup 失败] URL: {url}, Error: {e}")

          
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            extracted = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            if extracted and len(extracted) > 100:
                return extracted
    except Exception as e:
        # --- MODIFIED ---
        logging.warning(f"[Trafilatura 失败] URL: {url}, Error: {e}")

    return ""



def get_ai_structured_summary(full_text: str, company_name: str) -> Optional[AIInsight]:
    """调用Gemini AI模型生成结构化的JSON情报（已修正兼容Gemini 1.5）"""
    if not GEMINI_API_KEY:
        st.error("GEMINI_API_KEY 未在环境变量中设置！")
        return None
    if not full_text or len(full_text.strip()) < 50:
        # 如果文本内容太少，直接返回提示，不调用API
        return AIInsight(event_type="内容不足", key_entities="无", sentiment="中性", summary="未能从新闻链接中提取足够内容进行分析。")

    # 优化的Prompt，更清晰地指示模型输出JSON
    prompt = f"""
    作为一名顶级的风险投资分析师，请仔细阅读以下关于“{company_name}”公司的新闻文章内容。
    你的任务是，从文章中提炼出最关键的商业情报，并严格按照JSON格式返回一个包含以下键的对象：
    - "event_type": (string) 总结新闻的核心事件类型 (例如: '新一轮融资', '产品发布', '高管变动', '战略合作', '负面消息').
    - "key_entities": (string) 事件中涉及的关键实体，用逗号分隔 (例如: '投资方A, 合作伙伴B').
    - "sentiment": (string) 必须是 "正面", "中性", "负面" 其中之一.
    - "summary": (string) 对整个事件的简明扼要的总结.

    --- 文章内容如下 ---
    {full_text[:12000]}
    """
    
    # 简化的Payload，这是修正的核心
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.5, # 可以适当调整创造性
        }
    }
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=90)
        
        # 即使状态码不是200，也打印出返回内容以帮助调试
        if response.status_code != 200:
            st.error(f"AI模型返回错误，状态码: {response.status_code}")
            st.error(f"错误详情: {response.text}")
            return None

        result = response.json()

        if "candidates" in result and result["candidates"]:
            # Gemini 1.5 在JSON模式下，内容在 'text' 字段里
            json_text = result["candidates"][0]["content"]["parts"][0]["text"]
            # 使用 Pydantic 模型进行验证和解析
            return AIInsight.model_validate_json(json_text)
        else:
            # 处理没有 candidate 但有 error 的情况
            error_message = result.get('error', {}).get('message', '未知错误')
            st.error(f"AI分析失败: {error_message}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"网络请求失败，无法调用AI模型: {e}")
        return None
    except Exception as e:
        st.error(f"解析AI模型返回时发生未知错误: {e}")
        return None