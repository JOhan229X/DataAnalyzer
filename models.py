# models.py

from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# --- 用于情报分析Agent的模型 ---
class AIInsight(BaseModel):
    event_type: str = Field(..., description="总结新闻的核心事件类型，例如 '新一轮融资', '产品发布', '高管变动', '战略合作', '市场扩张', '负面消息' 等。")
    key_entities: str = Field(..., description="事件中涉及的关键实体，如投资方、合作伙伴、产品名称、核心人物等，用逗号分隔。")
    sentiment: Literal["正面", "中性", "负面"] = Field(..., description="根据文章内容判断的整体市场情绪。")
    summary: str = Field(..., description="对整个事件的简明扼要的总结，不超过200字。")

# --- 用于竞争力评估的模型 ---
class CompetitiveInput(BaseModel):
    tech_barrier_status: Literal[
        '已量产并交付≥100台', '公开 Demo + 顶会 / 核心专利 ≥3 件',
        '仅有专利或论文 ≥1 件', '无任何公开技术成果'
    ]
    market_validation_status: Literal[
        '已获得具有约束力的大额商业合同', '已获得有少量预付款的合同',
        '仅有战略合作新闻无金额', '无任何客户背书'
    ]
    team_status: Literal[
        '知名专家主动加盟', '形成由多位“明星”人员组成的核心团队',
        '普通社招为主', '无明星背景且团队停滞'
    ]

# --- 用于财务预测的模型 ---
class B2BContract(BaseModel):
    contract_name: str
    value: float = Field(..., gt=0)
    sign_date_str: str
    payment_terms_months: int = Field(..., ge=0)
    decay_factor: float = Field(0.95, ge=0, le=1)

class FinancialInput(BaseModel):
    initial_cash: float = Field(..., gt=0)
    monthly_burn: float = Field(..., gt=0)
    b2c_monthly_revenue: float = Field(0, ge=0)
    b2b_contracts: List[B2BContract] = []
    months_to_project: int = 36

class ScenarioInput(BaseModel):
    upfront_cost: float = Field(0, description="项目前期一次性投入/融资金额")
    monthly_extra_burn: float = Field(0, ge=0, description="项目每月新增成本")
    revenue_delay_months: int = Field(0, ge=0, description="项目回报延迟月数")
    monthly_revenue: float = Field(0, ge=0, description="项目每月产生收入")

class FundingRound(BaseModel):
    round_name: str         # 融资轮次，如 "A轮", "战略投资"
    date: str               # 融资日期
    amount: str             # 融资金额，如 "数亿元人民币", "$50M"
    investors: List[str]    # 投资方列表

class PatentInfo(BaseModel):
    name: str               # 专利名称
    type: str               # 专利类型，如 "发明专利"
    application_date: str   # 申请日期

class CompanyProfile(BaseModel):
    company_name: str
    legal_representative: str   # 法定代表人
    registered_capital: str     # 注册资本
    establishment_date: str     # 成立日期
    business_scope: str         # 经营范围
    funding_history: List[FundingRound] = [] # 融资历史
    patent_info: List[PatentInfo] = []       # 专利信息