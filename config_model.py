import os
from openai import OpenAI

# 检查API密钥是否已设置
api_key = os.environ.get("DASHSCOPE_API_KEY")
if not api_key:
    print("警告：环境变量 DASHSCOPE_API_KEY 未设置")
    print("请在系统环境变量中设置您的阿里云API密钥，或者在代码中直接设置")
    print("例如：api_key='your-api-key-here'")
    # 设置一个占位符，避免启动时报错
    api_key = 'placeholder-key-not-set'

# 创建OpenAI客户端
client = None
try:
    client = OpenAI(
        api_key=api_key,
        # 使用北京地域的兼容模式端点
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
except Exception as e:
    print(f"警告：创建OpenAI客户端失败: {e}")