#import numpy as np
# np.random.seed(0)
# x1=np.random.randint(20,size=10)   #0-9，随机六个数
# x2=np.random.randint(10,size=(3,4)) #0-9，随机3*4数
# x3=np.random.randint(10,size=(3,4,5))
# x4=x2[::1,::-1]
# x5=x1[1:3:]
# x6=x1[::2]
# x7=np.arange(10)
# print(x7[5::2])
# print(x1)
# print(x2)
# print(x2[2])
# print(x5)
# print(x6)        
# x7=x2[:2,:2]
# x7[0,0]=83
# print(x2,x2[:2,:2])

# copy=x2[:3,:3].copy()
# copy[0,0]=99
# print(copy,x2) 
# a=np.array([1,2,3])
# a.reshape((1,3))
# print(a)
# a=np.random.normal(0,1.5,(2,3))
# print(a)
# a=np.eye(3)
# print(a)

# test_connection.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

print("--- 开始连接测试 ---")

# 1. 加载环境变量 (确保您的 .env 文件中有 GEMINI_API_KEY)
print("步骤1: 正在加载 .env 文件...")
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("错误: 未能在 .env 文件或环境变量中找到 GEMINI_API_KEY！")
    exit()

print("成功加载API密钥。")

# 2. 尝试初始化LLM模型
print("\n步骤2: 正在初始化 ChatGoogleGenerativeAI...")
try:
    # 我们将同时测试两个模型，看哪个能通
    # llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=api_key)
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key)
    print("模型初始化成功！")
except Exception as e:
    print(f"模型初始化失败！错误: {e}")
    exit()

# 3. 发起一次最简单的调用
print("\n步骤3: 正在向Google服务器发起调用（请耐心等待）...")
try:
    response = llm.invoke("用中文说'你好'")
    print("\n--- ✅ 连接成功！---")
    print(f"AI的回复是: {response.content}")
except Exception as e:
    print("\n--- ❌ 连接失败！---")
    print(f"调用时发生错误: {e}")
    print("\n失败原因分析:")
    print("1. 请检查您的网络连接，是否可以正常访问 aistudio.google.com。")
    print("2. 如果您在中国大陆，可能需要设置网络代理才能连接到Google服务器。")
    print("3. 请确认您的API密钥是否有效，以及对应的Google Cloud项目是否已启用计费。")