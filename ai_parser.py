import json
import logging
import re
from typing import Dict, Optional
from config_model import client

logger = logging.getLogger(__name__)


def extract_valuation_metrics(raw_html: str) -> Optional[Dict]:
    """
    使用大模型从网页源码中提取估值指标
    
    Args:
        raw_html: 网页源码或文本内容
        
    Returns:
        包含估值指标的字典，格式为：
        {
            "industry_rank": 行业排名（整数）,
            "dynamic_pe": 当前动态PE（浮点数）,
            "hist_avg_pe": 历史平均PE（浮点数）,
            "hist_max_pe": 历史最高PE（浮点数）,
            "hist_min_pe": 历史最低PE（浮点数）
        }
        如果提取失败返回 None
    """
    try:
        logger.info("开始使用 AI 解析估值指标")
        
        # 截取关键文本，节省 Token
        # 查找包含 "pe" 或 "排名" 关键字的位置
        keywords = ["pe", "排名", "市盈率", "估值", "PE", "Rank"]
        start_pos = len(raw_html)
        
        for keyword in keywords:
            pos = raw_html.lower().find(keyword.lower())
            if pos != -1 and pos < start_pos:
                start_pos = pos
        
        # 如果找到关键字，截取前后 3000 个字符
        if start_pos < len(raw_html):
            start = max(0, start_pos - 1500)
            end = min(len(raw_html), start_pos + 1500)
            relevant_text = raw_html[start:end]
            logger.info(f"截取相关文本，长度: {len(relevant_text)} 字符")
        else:
            # 如果没找到关键字，使用前 5000 字符
            relevant_text = raw_html[:5000]
            logger.info(f"未找到关键字，使用前 5000 字符")
        
        # 构造提示词
        prompt = """你是一个专业的金融数据提取助手。请从这段网页源码中寻找该股票的以下估值指标：

1. 行业排名（industry_rank）：该股票在行业中的排名
2. 当前动态PE（dynamic_pe）：当前的动态市盈率
3. 历史平均PE（hist_avg_pe）：历史平均市盈率
4. 历史最高PE（hist_max_pe）：历史最高市盈率
5. 历史最低PE（hist_min_pe）：历史最低市盈率

要求：
- 如果找到数据，请以 JSON 格式返回，字段名使用英文
- 如果某个指标未找到，相应字段返回 null
- 排名返回整数，PE值返回浮点数（保留2位小数）
- 只返回 JSON，不要包含其他说明文字

网页源码如下：
""" + relevant_text
        
        logger.info("调用大模型进行数据提取")
        
        # 调用大模型
        response = client.chat.completions.create(
            model="qwen-max",
            messages=[
                {"role": "system", "content": "你是一个专业的金融数据提取助手，擅长从网页源码中提取结构化数据。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        # 获取响应
        result_text = response.choices[0].message.content.strip()
        logger.info(f"AI 原始响应: {result_text}")
        
        # 解析 JSON
        # 尝试提取 JSON 部分（可能包含在 markdown 代码块中）
        json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(1)
        else:
            # 尝试提取纯 JSON
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)
        
        result = json.loads(result_text)
        logger.info(f"AI 解析结果: {result}")
        
        # 验证并转换数据类型
        validated_result = {
            "industry_rank": _safe_int(result.get("industry_rank")),
            "dynamic_pe": _safe_float(result.get("dynamic_pe")),
            "hist_avg_pe": _safe_float(result.get("hist_avg_pe")),
            "hist_max_pe": _safe_float(result.get("hist_max_pe")),
            "hist_min_pe": _safe_float(result.get("hist_min_pe"))
        }
        
        logger.info(f"验证后的结果: {validated_result}")
        logger.info("✅ [AI Insight] 估值指标已通过模型语义识别成功补全")
        
        return validated_result
        
    except json.JSONDecodeError as e:
        logger.error(f"AI 返回的 JSON 解析失败: {e}")
        logger.error(f"原始响应: {result_text if 'result_text' in locals() else 'N/A'}")
        return None
    except Exception as e:
        logger.exception(f"AI 解析估值指标失败: {e}")
        return None


def extract_company_nature(raw_text: str) -> Optional[str]:
    """
    使用大模型从文本中提取企业性质
    
    Args:
        raw_text: 包含企业信息的文本（可以是 JSON 或网页源码）
        
    Returns:
        企业性质字符串，如"国有企业"、"民营企业"等
        如果提取失败返回 None
    """
    try:
        logger.info("开始使用 AI 解析企业性质")
        
        # 截取关键文本，节省 Token
        # 查找包含企业性质相关关键字的位置
        keywords = ["企业性质", "公司性质", "控股股东", "实际控制人", "gsxz", "CompanyNature"]
        start_pos = len(raw_text)
        
        for keyword in keywords:
            pos = raw_text.lower().find(keyword.lower())
            if pos != -1 and pos < start_pos:
                start_pos = pos
        
        # 如果找到关键字，截取前后 2000 个字符
        if start_pos < len(raw_text):
            start = max(0, start_pos - 1000)
            end = min(len(raw_text), start_pos + 1000)
            relevant_text = raw_text[start:end]
            logger.info(f"截取相关文本，长度: {len(relevant_text)} 字符")
        else:
            # 如果没找到关键字，使用前 3000 字符
            relevant_text = raw_text[:3000]
            logger.info(f"未找到关键字，使用前 3000 字符")
        
        # 构造提示词
        prompt = """你是一个专业的金融数据提取助手。请从这段文本中提取该股票的企业性质。

企业性质通常包括：国有企业、民营企业、外资企业、合资企业、集体企业等。

要求：
- 如果找到企业性质，请直接返回企业性质的名称（如"国有企业"、"民营企业"等）
- 如果未找到，返回 null
- 只返回企业性质名称，不要包含其他说明文字

文本内容如下：
""" + relevant_text
        
        logger.info("调用大模型进行企业性质提取")
        
        # 调用大模型
        response = client.chat.completions.create(
            model="qwen-max",
            messages=[
                {"role": "system", "content": "你是一个专业的金融数据提取助手，擅长从文本中提取企业信息。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        # 获取响应
        result = response.choices[0].message.content.strip()
        logger.info(f"AI 原始响应: {result}")
        
        # 清理响应
        if result.lower() == "null" or result.lower() == "n/a":
            return None
        
        # 移除可能的引号
        result = result.strip('"\'')
        
        logger.info(f"提取的企业性质: {result}")
        logger.info("✅ [AI Insight] 企业性质已通过模型语义识别成功补全")
        
        return result
        
    except Exception as e:
        logger.exception(f"AI 解析企业性质失败: {e}")
        return None


def _safe_int(value) -> Optional[int]:
    """安全转换为整数"""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return int(value)
        # 尝试从字符串中提取数字
        if isinstance(value, str):
            match = re.search(r'\d+', value)
            if match:
                return int(match.group())
        return None
    except (ValueError, TypeError):
        return None


def _safe_float(value) -> Optional[float]:
    """安全转换为浮点数"""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return float(value)
        # 尝试从字符串中提取数字
        if isinstance(value, str):
            match = re.search(r'\d+\.?\d*', value)
            if match:
                return float(match.group())
        return None
    except (ValueError, TypeError):
        return None
