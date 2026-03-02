import json
import logging
import re
from typing import Dict, Optional, List
from config_model import client

logger = logging.getLogger(__name__)


def ai_extract_metrics(text: str, indicators: List[str]) -> Optional[Dict]:
    """
    使用 AI 从文本中提取指定的估值指标
    
    Args:
        text: 包含估值数据的文本（HTML 或 JSON）
        indicators: 需要提取的指标列表，如 ["行业排名", "动态PE", "历史平均PE", "历史最高PE", "历史最低PE"]
        
    Returns:
        包含提取指标的字典，格式为：
        {
            "industry_rank": 行业排名（整数）,
            "dynamic_pe": 动态PE（浮点数）,
            "hist_avg_pe": 历史平均PE（浮点数）,
            "hist_max_pe": 历史最高PE（浮点数）,
            "hist_min_pe": 历史最低PE（浮点数）
        }
        如果提取失败返回 None
    """
    try:
        logger.info(f"[AI] 开始提取指标: {indicators}")
        
        # 截取关键文本，节省 Token
        # 查找包含关键字的位置
        keywords = ["pe", "排名", "市盈率", "估值", "PE", "Rank", "行业", "历史"]
        start_pos = len(text)
        
        for keyword in keywords:
            pos = text.lower().find(keyword.lower())
            if pos != -1 and pos < start_pos:
                start_pos = pos
        
        # 如果找到关键字，截取前后 3000 个字符
        if start_pos < len(text):
            start = max(0, start_pos - 1500)
            end = min(len(text), start_pos + 1500)
            relevant_text = text[start:end]
            logger.info(f"[AI] 截取相关文本，长度: {len(relevant_text)} 字符")
        else:
            # 如果没找到关键字，使用前 5000 字符
            relevant_text = text[:5000]
            logger.info(f"[AI] 未找到关键字，使用前 5000 字符")
        
        # 构造指标说明
        indicator_desc = "\n".join([f"- {ind}" for ind in indicators])
        
        # 构造提示词
        prompt = f"""你是一个专业的金融数据提取助手。请从这段网页源码或 JSON 数据中提取以下估值指标：

{indicator_desc}

要求：
1. 如果找到数据，请以 JSON 格式返回，字段名使用英文：
   - industry_rank: 行业排名（整数）
   - dynamic_pe: 动态市盈率（浮点数，保留2位小数）
   - hist_avg_pe: 历史平均市盈率（浮点数，保留2位小数）
   - hist_max_pe: 历史最高市盈率（浮点数，保留2位小数）
   - hist_min_pe: 历史最低市盈率（浮点数，保留2位小数）

2. 如果某个指标未找到，相应字段返回 null

3. 只返回 JSON，不要包含其他说明文字

4. 注意：
   - 排名可能是"第1名"、"行业排名: 1"等格式，提取数字即可
   - PE值可能是"21.5倍"、"PE: 21.5"等格式，提取数字即可
   - 历史数据可能在"历史PE"、"PE历史"、"市盈率历史"等字段中

网页源码或 JSON 数据如下：
""" + relevant_text
        
        logger.info(f"[AI] 调用大模型进行数据提取")
        
        # 调用大模型
        response = client.chat.completions.create(
            model="qwen-max",
            messages=[
                {"role": "system", "content": "你是一个专业的金融数据提取助手，擅长从网页源码和 JSON 数据中提取结构化数据。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        # 获取响应
        result_text = response.choices[0].message.content.strip()
        logger.info(f"[AI] 原始响应: {result_text}")
        
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
        logger.info(f"[AI] 解析结果: {result}")
        
        # 验证并转换数据类型
        validated_result = {
            "industry_rank": _safe_int(result.get("industry_rank")),
            "dynamic_pe": _safe_float(result.get("dynamic_pe")),
            "hist_avg_pe": _safe_float(result.get("hist_avg_pe")),
            "hist_max_pe": _safe_float(result.get("hist_max_pe")),
            "hist_min_pe": _safe_float(result.get("hist_min_pe"))
        }
        
        logger.info(f"[AI] 验证后的结果: {validated_result}")
        logger.info(f"✅ [AI Insight] 估值指标已通过模型语义识别成功补全")
        
        return validated_result
        
    except json.JSONDecodeError as e:
        logger.error(f"[AI] JSON 解析失败: {e}")
        logger.error(f"[AI] 原始响应: {result_text if 'result_text' in locals() else 'N/A'}")
        return None
    except Exception as e:
        logger.exception(f"[AI] 提取指标失败: {e}")
        return None


def ai_extract_company_nature(text: str) -> Optional[str]:
    """
    使用 AI 从文本中提取企业性质
    
    Args:
        text: 包含企业信息的文本（可以是 JSON 或网页源码）
        
    Returns:
        企业性质字符串，如"国有企业"、"民营企业"等
        如果提取失败返回 None
    """
    try:
        logger.info("[AI] 开始提取企业性质")
        
        # 截取关键文本，节省 Token
        keywords = ["企业性质", "公司性质", "控股股东", "实际控制人", "gsxz", "CompanyNature", "ORG_PROFILE"]
        start_pos = len(text)
        
        for keyword in keywords:
            pos = text.lower().find(keyword.lower())
            if pos != -1 and pos < start_pos:
                start_pos = pos
        
        # 如果找到关键字，截取前后 2000 个字符
        if start_pos < len(text):
            start = max(0, start_pos - 1000)
            end = min(len(text), start_pos + 1000)
            relevant_text = text[start:end]
            logger.info(f"[AI] 截取相关文本，长度: {len(relevant_text)} 字符")
        else:
            # 如果没找到关键字，使用前 3000 字符
            relevant_text = text[:3000]
            logger.info(f"[AI] 未找到关键字，使用前 3000 字符")
        
        # 构造提示词
        prompt = """你是一个专业的金融数据提取助手。请从这段文本中提取该股票的企业性质。

企业性质通常包括：国有企业、民营企业、外资企业、合资企业、集体企业、地方国有企业、中央国有企业等。

要求：
1. 如果找到企业性质，请直接返回企业性质的名称（如"国有企业"、"民营企业"等）
2. 如果未找到，返回 null
3. 只返回企业性质名称，不要包含其他说明文字
4. 注意：
   - 可以从"控股股东"、"实际控制人"等字段推断企业性质
   - 如果控股股东是"国资委"、"地方政府"等，可能是国有企业
   - 如果控股股东是"个人"、"家族"等，可能是民营企业

文本内容如下：
""" + relevant_text
        
        logger.info("[AI] 调用大模型进行企业性质提取")
        
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
        logger.info(f"[AI] 原始响应: {result}")
        
        # 清理响应
        if result.lower() == "null" or result.lower() == "n/a":
            return None
        
        # 移除可能的引号
        result = result.strip('"\'')
        
        logger.info(f"[AI] 提取的企业性质: {result}")
        logger.info(f"✅ [AI Insight] 企业性质已通过模型语义识别成功补全")
        
        return result
        
    except Exception as e:
        logger.exception(f"[AI] 提取企业性质失败: {e}")
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
