# agent_brain.py (V3.1 - 统一使用API Key认证)

import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
import streamlit as st
import pandas as pd
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# --- 导入我们所有的后台模块和工具 ---
from intelligence import get_ai_structured_summary, search_news_links, browse_article_text
from mock_data_provider import get_mock_company_data
from database import add_to_watchlist, get_watchlist
from engine import generate_cash_flow_forecast, calculate_runway_and_score, analyze_funding_urgency
from models import FinancialInput


class FinancialQueryInput(BaseModel):
    initial_cash: float = Field(description="公司初始现金，单位是万元")
    monthly_burn: float = Field(description="公司每月运营成本或消耗，单位是万元")
    b2c_monthly_revenue: float = Field(0, description="公司每月B2C业务收入，单位是万元")

def get_company_profile_tool(company_name: str) -> str:
    """获取一家公司的核心档案信息，如法人、注册资本、融资历史和专利。"""
    print(f"Executing get_company_profile_tool for: {company_name}")
    profile = get_mock_company_data(company_name)
    if profile:
        return str(profile.model_dump())
    return "未在数据库中找到该公司信息。"

def get_company_profile_tool(company_name: str) -> str:
    """获取一家公司的核心档案信息，如法人、注册资本、融资历史和专利。"""
    print(f"Executing get_company_profile_tool for: {company_name}")
    profile = get_mock_company_data(company_name)
    if profile:
        return str(profile.model_dump())
    return "未在数据库中找到该公司信息。"

def get_latest_news_summary_tool(company_name: str) -> str:
    """获取一家公司最新的、由AI总结的新闻摘要。"""
    print(f"Executing get_latest_news_summary_tool for: {company_name}")
    news_items = search_news_links(company_name, num_articles=1)
    if news_items:
        full_text = browse_article_text(news_items[0].get("url"))
        ai_summary = get_ai_structured_summary(full_text, company_name)
        if ai_summary:
            return str(ai_summary.model_dump())
    return "未找到该公司近期相关新闻。"

def analyze_financial_scenario_tool(query: str) -> str:
    """
    分析和预测公司在特定财务情景下的现金流状况。
    输入应该是一个清晰描述财务参数的自然语言问题，例如：
    '分析一家初始现金200万，月消耗30万，每月B2C收入1.5万的公司' 或
    '如果公司A拿到一笔500万的融资，会怎么样'
    """
    print(f"Executing analyze_financial_scenario_tool with query: {query}")
    llm = st.session_state.llm 

    # 1. 设置 Pydantic Parser
    parser = PydanticOutputParser(pydantic_object=FinancialQueryInput)
    
    # 2. 创建包含格式化指令的 Prompt
    prompt_template = """
    请从以下问题中提取财务参数。
    所有金额单位都应为“万元”，例如“200万”应为200。
    如果问题中没有提到某个值，请使用默认值0。
    {format_instructions}
    
    问题: "{query}"
    """
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # 3. 创建Chain并执行
    chain = prompt | llm | parser
    
    try:
        # 4. 解析结果
        params = chain.invoke({"query": query})
        
        fin_input = FinancialInput(
            initial_cash=params.initial_cash,
            monthly_burn=params.monthly_burn,
            b2c_monthly_revenue=params.b2c_monthly_revenue
        )
        
        if fin_input.monthly_burn <= 0 and fin_input.initial_cash <= 0:
            return "信息不足，无法进行财务分析。请输入初始现金和月度消耗。"
            
        # 5. 执行分析并返回结果
        cash_flow_df = generate_cash_flow_forecast(fin_input)
        runway, score = calculate_runway_and_score(cash_flow_df)
        funding_analysis = analyze_funding_urgency(score)
        df_markdown = cash_flow_df.head(6).to_markdown()
        
        result = f"""
### 财务情景分析报告
根据您提供的信息，分析结果如下：

- **现金生命线 (Runway)**: {runway} 个月
- **财务健康评分**: {score*100:.0f}/100
- **融资建议**: {funding_analysis['suggestion']}

#### 未来6个月现金流预测 (单位: 万元)
{df_markdown}
"""
        return result
    except Exception as e:
        print(f"财务分析工具出错: {e}")
        return f"抱歉，解析您的财务问题时出错。请确保问题中包含了明确的数字，例如 '初始现金200万'。错误详情: {e}"

tools = [
    Tool(
        name="GetCompanyProfile",
        func=get_company_profile_tool,
        description="用于查询一家公司的基本档案、融资历史或专利信息。输入应该是一家公司的准确名称。",
    ),
    Tool(
        name="GetLatestNewsSummary",
        func=get_latest_news_summary_tool,
        description="用于获取一家公司最新的市场动态和新闻摘要。输入应该是一家公司的准确名称。",
    ),
    Tool(
        name="AnalyzeFinancialScenario",
        func=analyze_financial_scenario_tool,
        description="用于进行公司财务和现金流的模拟与预测。当用户问题包含'现金流'、'生命线'、'融资'、'预测'、'分析'等关键词，并提及具体金额时，应使用此工具。",
    ),
    Tool(
        name="AddToWatchlist",
        func=add_to_watchlist,
        description="当用户想要监控、追踪或关注一家公司时使用。输入应该是一家公司的准确名称。",
    ),
    Tool(
        name="GetWatchlist",
        func=lambda x="": ", ".join(get_watchlist()) or "监控列表为空。",
        description="当用户想要查看当前监控列表中的所有公司时使用。此工具不需要输入。",
    ),
]

# ... [Prompt模板部分保持不变] ...
prompt_template = """
你是一个名为 'InsightBot' 的顶尖风险投资分析AI助手。你的沟通风格必须专业、简洁、数据驱动。

你有以下工具可以使用：
{tools}

请使用以下格式进行思考和回应：
Question: 你必须回答的用户问题
Thought: 你应该时刻思考该做什么。你需要分析用户的问题，并利用对话历史({chat_history})来理解上下文。
Action: 你要采取的行动，必须是 [{tool_names}] 中的一个
Action Input: 该行动的输入
Observation: 该行动返回的结果
...（这个Thought/Action/Action Input/Observation的过程可以重复N次）
Thought: 我现在拥有足够的信息来回答用户的问题了。
Final Answer: 对原始问题的最终中文回答，确保回答专业、简洁且格式清晰。如果结果包含表格，请使用Markdown格式化。

开始！

之前的对话内容:
{chat_history}

新问题: {input}
Thought:{agent_scratchpad}
"""
prompt = PromptTemplate.from_template(prompt_template)


# --- 3. 初始化LLM, Agent, 和记忆模块 ---
# ✅ 这里是核心修改部分
def initialize_agent():
    """初始化LLM和Agent，但不包含记忆。"""
    if "agent_executor" not in st.session_state:
        print("Initializing Agent for the first time...")
        
        # 从环境变量中获取API Key
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY 环境变量未设置！请在.env文件中配置。")
        
        # 初始化模型时，明确传入 google_api_key 参数
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest", 
            temperature=0,
            google_api_key=gemini_api_key # <-- 核心改动在这里
        )
        
        agent = create_react_agent(llm, tools, prompt)
        
        st.session_state.agent = agent
        st.session_state.llm = llm

# ... [主函数 get_agent_response 保持不变] ...
def get_agent_response(user_input: str, memory) -> str:
    """接收用户输入和记忆，返回Agent的最终回答。"""
    try:
        agent_executor = AgentExecutor(
            agent=st.session_state.agent,
            tools=tools,
            memory=memory, 
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=30  
        )
        
        response = agent_executor.invoke({"input": user_input})
        return response.get('output', "Agent没有返回预期的输出。")
    except Exception as e:
        print(f"Agent执行出错: {e}")
        return f"抱歉，处理您的请求时出错: {e}"