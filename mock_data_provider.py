# mock_data_provider.py

from models import CompanyProfile, FundingRound, PatentInfo
from typing import Optional

def get_mock_company_data(company_name: str) -> Optional[CompanyProfile]:
    """
    模拟的数据提供函数。
    在真实场景中，这里会是调用天眼查API并解析返回数据的逻辑。
    """
    # 我们可以为Demo中常用的一两个公司预置数据
    if "月之暗面" in company_name:
        return CompanyProfile(
            company_name="北京月之暗面科技有限公司",
            legal_representative="杨植麟",
            registered_capital="100万人民币",
            establishment_date="2023-04-17",
            business_scope="技术开发、技术推广、技术转让、技术咨询、技术服务...",
            funding_history=[
                FundingRound(round_name="天使轮", date="2023-06-01", amount="未披露", investors=["杨植麟"]),
                FundingRound(round_name="A轮", date="2023-10-01", amount="超2亿美元", investors=["红杉中国", "真格基金"]),
                FundingRound(round_name="B轮", date="2024-02-20", amount="超10亿美元", investors=["阿里巴巴", "小红书", "美团"])
            ],
            patent_info=[
                PatentInfo(name="一种基于大规模语言模型的对话系统", type="发明专利", application_date="2023-08-15"),
                PatentInfo(name="神经网络压缩与加速方法", type="发明专利", application_date="2023-09-02")
            ]
        )
    # 如果没有匹配的公司，可以返回None
    return None