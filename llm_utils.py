# -*- coding: utf-8 -*-
"""
LLM工具模块：使用大模型进行数据解析和提取
"""

import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# 检查API密钥是否已设置
api_key = os.environ.get("DASHSCOPE_API_KEY")
if not api_key:
    logger.warning("环境变量 DASHSCOPE_API_KEY 未设置")
    logger.warning("请在系统环境变量中设置您的阿里云API密钥")
    # 可以设置一个默认的示例密钥，实际使用时需要替换
    # api_key = 'your-api-key-here'

# 创建OpenAI客户端
client = OpenAI(
    api_key=api_key,
    # 使用北京地域的兼容模式端点
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 定义不同类型的提示词
PROMPT_TEMPLATES = {
    'company_nature': """从以下公司基本资料中提取'企业性质'（例如：中央国有企业、民营企业、地方国有企业、外资企业、合资企业、集体企业等），仅返回该短语，不要包含其他任何文字。

公司基本资料：
{content}

企业性质：""",

    'yiniu_industry_data': """从以下文本中提取：行业排名、当前动态PE、历史平均PE、历史最高PE、历史最低PE。请以标准 JSON 格式返回，Key 名对应为：industry_rank, dynamic_pe, hist_avg_pe, hist_max_pe, hist_min_pe。

文本内容：
{content}

请返回JSON格式：
{{
  "industry_rank": "行业排名",
  "dynamic_pe": "当前动态PE",
  "hist_avg_pe": "历史平均PE",
  "hist_max_pe": "历史最高PE",
  "hist_min_pe": "历史最低PE"
}}"""
}


def llm_parse_data(raw_content, prompt_type, max_retries=3):
    """
    使用大模型解析原始数据
    
    Args:
        raw_content: 原始内容（HTML、JSON等）
        prompt_type: 提示词类型（'company_nature' 或 'yiniu_industry_data'）
        max_retries: 最大重试次数
    
    Returns:
        解析后的数据，根据 prompt_type 返回不同类型：
        - company_nature: 返回字符串
        - yiniu_industry_data: 返回字典
        如果失败返回 None
    """
    if not api_key:
        logger.warning("DASHSCOPE_API_KEY 未设置，无法使用 LLM 解析")
        return None
    
    if prompt_type not in PROMPT_TEMPLATES:
        logger.error(f"未知的提示词类型: {prompt_type}")
        return None
    
    if not raw_content or len(raw_content.strip()) == 0:
        logger.warning("原始内容为空，无法解析")
        return None
    
    # 获取提示词模板
    prompt_template = PROMPT_TEMPLATES[prompt_type]
    
    # 限制内容长度，避免超出token限制
    max_content_length = 8000
    if len(raw_content) > max_content_length:
        logger.info(f"原始内容过长（{len(raw_content)}字符），截取前{max_content_length}字符")
        raw_content = raw_content[:max_content_length]
    
    # 构建完整提示词
    prompt = prompt_template.format(content=raw_content)
    
    # 尝试调用大模型
    for attempt in range(max_retries):
        try:
            logger.info(f"使用 LLM 解析数据（类型: {prompt_type}，尝试 {attempt + 1}/{max_retries}）")
            
            response = client.chat.completions.create(
                model="qwen-plus",  # 使用通义千问模型
                messages=[
                    {"role": "system", "content": "你是一个专业的数据提取助手，擅长从非结构化文本中提取关键信息。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 降低温度，提高确定性
                max_tokens=500,
            )
            
            # 获取响应内容
            result = response.choices[0].message.content.strip()
            logger.info(f"LLM 响应: {result}")
            
            # 根据提示词类型处理响应
            if prompt_type == 'company_nature':
                # 企业性质：直接返回字符串
                if result:
                    logger.info(f"成功提取企业性质: {result}")
                    return result
                else:
                    logger.warning("LLM 返回的企业性质为空")
                    return None
            
            elif prompt_type == 'yiniu_industry_data':
                # 亿牛网数据：解析 JSON
                try:
                    # 尝试直接解析 JSON
                    parsed_data = json.loads(result)
                    
                    # 验证必需字段
                    required_fields = ['industry_rank', 'dynamic_pe', 'hist_avg_pe', 'hist_max_pe', 'hist_min_pe']
                    for field in required_fields:
                        if field not in parsed_data:
                            logger.warning(f"LLM 返回的 JSON 缺少字段: {field}")
                            parsed_data[field] = 0
                    
                    # 转换数值类型
                    for field in required_fields:
                        if isinstance(parsed_data[field], str):
                            # 尝试从字符串中提取数字
                            import re
                            match = re.search(r'(\d+\.?\d*)', parsed_data[field])
                            if match:
                                parsed_data[field] = float(match.group(1))
                            else:
                                parsed_data[field] = 0
                        elif parsed_data[field] is None:
                            parsed_data[field] = 0
                    
                    logger.info(f"成功提取亿牛网数据: {parsed_data}")
                    return parsed_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"LLM 返回的不是有效的 JSON 格式: {e}")
                    logger.error(f"原始响应: {result}")
                    
                    # 尝试从响应中提取 JSON
                    import re
                    json_match = re.search(r'\{[^}]+\}', result, re.DOTALL)
                    if json_match:
                        try:
                            parsed_data = json.loads(json_match.group(0))
                            logger.info(f"从响应中提取到 JSON: {parsed_data}")
                            return parsed_data
                        except:
                            logger.error("无法从响应中提取 JSON")
                    
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"LLM 解析失败（尝试 {attempt + 1}/{max_retries}）: {e}")
            import traceback
            traceback.print_exc()
            
            if attempt < max_retries - 1:
                logger.info(f"等待 2 秒后重试...")
                import time
                time.sleep(2)
    
    logger.error(f"LLM 解析失败，已达到最大重试次数 {max_retries}")
    return None


def test_llm_connection():
    """测试 LLM 连接是否正常"""
    if not api_key:
        logger.warning("DASHSCOPE_API_KEY 未设置，无法测试连接")
        return False
    
    try:
        logger.info("测试 LLM 连接...")
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "user", "content": "你好，请回复'连接成功'"}
            ],
            max_tokens=10,
        )
        
        result = response.choices[0].message.content.strip()
        logger.info(f"LLM 响应: {result}")
        
        if "成功" in result:
            logger.info("LLM 连接测试成功")
            return True
        else:
            logger.warning(f"LLM 响应不符合预期: {result}")
            return False
            
    except Exception as e:
        logger.error(f"LLM 连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 测试 LLM 连接
    test_llm_connection()
    
    # 测试企业性质提取
    test_content = """
    贵州茅台酒股份有限公司(以下简称"公司")成立于1999年11月20日,由中国贵州茅台酒厂(集团)有限责任公司(以下简称"茅台集团")作为主发起人,联合另外七家单位共同发起设立,目前控股股东为茅台集团。
    """
    
    result = llm_parse_data(test_content, 'company_nature')
    print(f"企业性质提取结果: {result}")
    
    # 测试亿牛网数据提取
    test_content2 = """
    行业排名：第1名
    当前动态PE：21.64
    历史平均PE：25.32
    历史最高PE：45.67
    历史最低PE：12.34
    """
    
    result2 = llm_parse_data(test_content2, 'yiniu_industry_data')
    print(f"亿牛网数据提取结果: {result2}")
