# test_trafilatura_v4.py
import warnings
import requests
import ssl
from requests.adapters import HTTPAdapter
# test_trafilatura_v4.py (新的 import)
from urllib3.poolmanager import PoolManager
from urllib3.util.ssl_ import create_urllib3_context

import trafilatura

# --- Start of Advanced Network Configuration ---
# 定义一个强制使用特定TLS版本的上下文
# This is a workaround for proxies that have issues with modern TLS versions.
class TlsV12HttpAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        # ciphers list is a balance between security and compatibility
        ciphers = (
            'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:'
            'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:'
            'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:'
            'DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384'
        )
        context = create_urllib3_context(
            ciphers=ciphers,
            ssl_version=ssl.PROTOCOL_TLSv1_2
        )
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=context
        )
# --- End of Advanced Network Configuration ---


# 忽略不安全的HTTPS请求警告
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# 创建一个 session 对象，并挂载我们的自定义适配器
session = requests.Session()
session.mount("https://", TlsV12HttpAdapter())
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

# --- Start of Test ---
URL = "https://news.sina.com.cn/world/2025-08-18/doc-imzixcmf8216758.shtml"
print(f"--- 正在使用高级网络配置进行最终测试 ---")
print(f"URL: {URL}")

try:
    # 使用配置好的 session 对象发起请求，并禁用证书验证
    response = session.get(URL, timeout=30, verify=False)

    print(f"HTTP 状态码: {response.status_code}")
    response.raise_for_status()

    text = trafilatura.extract(response.text)

    if text:
        print("✅ 提取成功! 内容预览:")
        print(text[:150].replace('\n', ' '))
    else:
        print("❌ 提取失败: Trafilatura 未能解析出内容。")

except Exception as e:
    print(f"❌ 测试出现严重异常: {e}")
print("="*20 + "\n")