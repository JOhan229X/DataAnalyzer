

import pandas as pd
from dateutil.relativedelta import relativedelta
from typing import Tuple, Optional
from models import CompetitiveInput, FinancialInput, ScenarioInput

def score_competitiveness(inputs: CompetitiveInput) -> dict:
    scores = {"技术壁垒": 0.0, "市场验证": 0.0, "人才团队": 0.0}
    if inputs.tech_barrier_status == '已量产并交付≥100台': scores["技术壁垒"] = 1.0
    elif inputs.tech_barrier_status == '公开 Demo + 顶会 / 核心专利 ≥3 件': scores["技术壁垒"] = 0.75
    elif inputs.tech_barrier_status == '仅有专利或论文 ≥1 件': scores["技术壁垒"] = 0.5
    if inputs.market_validation_status == '已获得具有约束力的大额商业合同': scores["市场验证"] = 1.0
    elif inputs.market_validation_status == '已获得有少量预付款的合同': scores["市场验证"] = 0.75
    elif inputs.market_validation_status == '仅有战略合作新闻无金额': scores["市场验证"] = 0.5
    if inputs.team_status == '知名专家主动加盟': scores["人才团队"] = 1.0
    elif inputs.team_status == '形成由多位“明星”人员组成的核心团队': scores["人才团队"] = 0.75
    elif inputs.team_status == '普通社招为主': scores["人才团队"] = 0.5
    return scores

def generate_cash_flow_forecast(inputs: FinancialInput, scenario: Optional[ScenarioInput] = None) -> pd.DataFrame:
    dates = pd.period_range(start=pd.to_datetime("today"), periods=inputs.months_to_project, freq='M')
    df = pd.DataFrame(index=dates, columns=['B2C收入', 'B2B回款', '项目收入', '总流入', '月度消耗', '项目消耗', '总消耗', '月度净现金流', '期末现金']).fillna(0.0)
    df['B2C收入'], df['月度消耗'] = inputs.b2c_monthly_revenue, inputs.monthly_burn
    if scenario:
        if scenario.revenue_delay_months < len(df):
            df.iloc[scenario.revenue_delay_months:, df.columns.get_loc('项目收入')] = scenario.monthly_revenue
        df['项目消耗'] = scenario.monthly_extra_burn
    for contract in inputs.b2b_contracts:
        payment_period = (pd.to_datetime(contract.sign_date_str) + relativedelta(months=contract.payment_terms_months)).to_period('M')
        if payment_period in df.index:
            df.loc[payment_period, 'B2B回款'] += contract.value * contract.decay_factor
    last_month_cash = inputs.initial_cash
    if scenario:
        last_month_cash += scenario.upfront_cost
    for period in df.index:
        df.loc[period, '总流入'] = df.loc[period, 'B2C收入'] + df.loc[period, 'B2B回款'] + df.loc[period, '项目收入']
        df.loc[period, '总消耗'] = df.loc[period, '月度消耗'] + df.loc[period, '项目消耗']
        df.loc[period, '月度净现金流'] = df.loc[period, '总流入'] - df.loc[period, '总消耗']
        df.loc[period, '期末现金'] = last_month_cash + df.loc[period, '月度净现金流']
        last_month_cash = df.loc[period, '期末现金']
    df.index = df.index.to_timestamp().strftime('%Y-%m')
    return df[['总流入', '总消耗', '月度净现金流', '期末现金']].round(2)

def calculate_runway_and_score(cash_flow_df: pd.DataFrame) -> Tuple[int, float]:
    try:
        runway_months = cash_flow_df.index.get_loc(cash_flow_df[cash_flow_df['期末现金'] < 0].index[0])
    except IndexError:
        runway_months = len(cash_flow_df)
    survival_score = min(runway_months / 36, 1.0)
    return runway_months, round(survival_score, 2)

def analyze_funding_urgency(survival_score: float) -> dict:
    if survival_score > 0.75: return {"level": "低", "suggestion": "现金流健康，无需或可选择性融资。"}
    elif 0.50 <= survival_score <= 0.74: return {"level": "中", "suggestion": "建议进行战略性融资，以加速发展。"}
    elif 0.25 <= survival_score <= 0.49: return {"level": "高", "suggestion": "融资需求较高，应优先考虑启动融资。"}
    else: return {"level": "紧急", "suggestion": "现金流即将耗尽，必须立即启动融资。"}

def check_project_feasibility(runway_months: int, project_duration: int, buffer_months: int = 6) -> dict:
    required_months = project_duration + buffer_months
    is_feasible = runway_months >= required_months
    reason = f"公司当前生命线({runway_months}个月){'足以' if is_feasible else '不足以'}覆盖项目周期加安全缓冲({required_months}个月)。"
    return {"feasible": is_feasible, "reason": reason}