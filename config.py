# -*- coding: utf-8 -*-
"""
配置文件：定义爬虫接口、数据字段映射和常量
"""

import time

# ========== 爬虫配置 ==========
class SpiderConfig:
    # 东方财富(Eastmoney) API配置
    EASTMONEY = {
        "base_url": "https://emweb.securities.eastmoney.com/PC_HSF10",
        "financial_reports": {
            "income": "F10_ProfitStatement",  # 利润表
            "balance": "F10_BalanceSheet",   # 资产负债表
            "cash_flow": "F10_CashFlowStatement"  # 现金流量表
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
            "Referer": "https://emweb.securities.eastmoney.com/"
        },
        "timeout": 10,
        "retry_times": 3,
        "retry_delay": 1
    }
    
    # 亿牛网(Yiniu) API配置
    YINIU = {
        "base_url": "https://eniu.com",
        "financial_reports": {
            "income": "api/v3/stock/financial/income",
            "balance": "api/v3/stock/financial/balance",
            "cash_flow": "api/v3/stock/financial/cash_flow"
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
            "Referer": "https://eniu.com/"
        },
        "timeout": 10,
        "retry_times": 3,
        "retry_delay": 1
    }
    
    # 雪球(Xueqiu) API配置
    XUEQIU = {
        "base_url": "https://xueqiu.com",
        "financial_reports": {
            "income": "v5/stock/finance/cn/income.json",
            "balance": "v5/stock/finance/cn/balance.json",
            "cash_flow": "v5/stock/finance/cn/cash_flow.json"
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
            "Referer": "https://xueqiu.com/"
        },
        "timeout": 10,
        "retry_times": 3,
        "retry_delay": 1
    }

# ========== 数据字段映射 ==========
class FieldMapping:
    # 基础信息区（A1 - F6）映射
    HEADER_INFO = {
        "title": {"row": 1, "col_start": 1, "col_end": 6, "key": "stock_name"},  # A1:F1 合并单元格
        "current_price": {"row": 2, "col": 2, "unit": "元", "key": "current_price"},  # B2
        "total_market_cap": {"row": 2, "col": 4, "unit": "亿元", "key": "total_market_cap"},  # D2
        "industry": {"row": 3, "col": 2, "unit": "文本", "key": "industry"},  # B3
        "pe_ratio": {"row": 3, "col": 4, "unit": "倍", "key": "pe_ratio"},  # D3
        "pb_ratio": {"row": 4, "col": 2, "unit": "倍", "key": "pb_ratio"},  # B4
        "cagr_5y": {"row": 4, "col": 4, "unit": "%", "key": "cagr_5y"}  # D4
    }
    
    # 财务指标区（Row 7-20）映射
    INDICATOR_MAP = {
        "total_revenue": {
            "row": 7,
            "unit": "亿元",
            "display_format": "numeric",
            "conversion_factor": 1e8,  # 原始数据为元，需除以1亿
            "decimal_places": 2
        },
        "revenue_growth": {
            "row": 8,
            "unit": "%",
            "display_format": "percentage",
            "decimal_places": 2
        },
        "net_profit": {
            "row": 9,
            "unit": "亿元",
            "display_format": "numeric",
            "conversion_factor": 1e8,  # 原始数据为元，需除以1亿
            "decimal_places": 2
        },
        "profit_growth": {
            "row": 10,
            "unit": "%",
            "display_format": "percentage",
            "decimal_places": 2
        },
        "roe": {
            "row": 11,
            "unit": "%",
            "display_format": "percentage",
            "decimal_places": 2,
            "note": "严禁写成LED"
        },
        "gross_margin": {
            "row": 12,
            "unit": "%",
            "display_format": "percentage",
            "decimal_places": 2
        },
        "net_margin": {
            "row": 13,
            "unit": "%",
            "display_format": "percentage",
            "decimal_places": 2
        },
        "net_profit_cash_ratio": {
            "row": 14,
            "unit": "%",
            "display_format": "percentage",
            "decimal_places": 2,
            "note": "经营现金流/净利润",
            "warning_threshold": 80  # 低于80%标记为红色
        },
        "debt_asset_ratio": {
            "row": 15,
            "unit": "%",
            "display_format": "percentage",
            "decimal_places": 2
        },
        "ocfps": {
            "row": 16,
            "unit": "元",
            "display_format": "numeric",
            "decimal_places": 2
        },
        "bps": {
            "row": 17,
            "unit": "元",
            "display_format": "numeric",
            "decimal_places": 2
        },
        "eps": {
            "row": 18,
            "unit": "元",
            "display_format": "numeric",
            "decimal_places": 2
        }
    }
    
    # 年份到列的映射（多列并行填充）
    YEAR_COLUMN_MAP = {
        2024: 2,  # B列
        2023: 3,  # C列
        2022: 4,  # D列
        2021: 5,  # E列
        2020: 6   # F列
    }
    
    # 旧的财务指标映射（保留用于兼容）
    FINANCIAL_INDICATORS = {
        "roe": {
            "2020": "L10",
            "2021": "N10",
            "2022": "P10",
            "2023": "R10",
            "2024": "T10",
            "2025": "V10"
        },
        "revenue_growth_rate": {
            "2020": "L11",
            "2021": "N11",
            "2022": "P11",
            "2023": "R11",
            "2024": "T11",
            "2025": "V11"
        },
        "gross_margin": {
            "2020": "L12",
            "2021": "N12",
            "2022": "P12",
            "2023": "R12",
            "2024": "T12",
            "2025": "V12"
        },
        "net_margin": {
            "2020": "L13",
            "2021": "N13",
            "2022": "P13",
            "2023": "R13",
            "2024": "T13",
            "2025": "V13"
        },
        "net_profit_cash_ratio": {
            "2020": "L14",
            "2021": "N14",
            "2022": "P14",
            "2023": "R14",
            "2024": "T14",
            "2025": "V14"
        },
        "debt_asset_ratio": {
            "2020": "L15",
            "2021": "N15",
            "2022": "P15",
            "2023": "R15",
            "2024": "T15",
            "2025": "V15"
        },
        "dividend_yield": {
            "2020": "L16",
            "2021": "N16",
            "2022": "P16",
            "2023": "R16",
            "2024": "T16",
            "2025": "V16"
        },
        "payout_ratio": {
            "2020": "L17",
            "2021": "N17",
            "2022": "P17",
            "2023": "R17",
            "2024": "T17",
            "2025": "V17"
        },
        "ocfps": {
            "2020": "L18",
            "2021": "N18",
            "2022": "P18",
            "2023": "R18",
            "2024": "T18",
            "2025": "V18"
        },
        "bps": {
            "2020": "L19",
            "2021": "N19",
            "2022": "P19",
            "2023": "R19",
            "2024": "T19",
            "2025": "V19"
        },
        "eps": {
            "2020": "L20",
            "2021": "N20",
            "2022": "P20",
            "2023": "R20",
            "2024": "T20",
            "2025": "V20"
        }
    }
    
    # 公司信息到Excel单元格的映射
    COMPANY_INFO = {
        "stock_code": "B9",
        "stock_name": "B10",
        "established_date": "B12",
        "listing_date": "C13",
        "company_nature": "C14",
        "industry": "C15",
        "total_market_cap": "C16",  # 单位：亿元
        "industry_rank": "C17"
    }
    
    # 估值指标到Excel单元格的映射
    VALUATION_INDICATORS = {
        "pe": "D13",
        "pb": "D17",
        "eps": "F8",
        "dividend_yield": "D10",
        "book_value_per_share": "D11",
        "current_pe": "F13",
        "current_pb": "F17"
    }
    
    # 情况表数据映射
    SITUATION_SHEET = {
        "business_main_operations": "B3",  # 主营业务构成
        "industry_position": "B4"  # 行业地位简述
    }

# ========== 常量定义 ==========
class Constants:
    # 单位转换系数
    UNIT_CONVERSION = {
        "ten_thousand_to_hundred_million": 0.0001,  # 万元转亿元
        "percent_to_decimal": 0.01  # 百分比转小数
    }
    
    # 小数位数
    DECIMAL_PLACES = 4
    
    # 异常处理值
    ERROR_VALUES = {
        "divide_by_zero": "N/A",
        "missing_data": "N/A",
        "invalid_value": "N/A"
    }
    
    # 审计校验阈值（净资产 + 当年利润 - 分红 ≈ 次年净资产 的允许偏差）
    AUDIT_THRESHOLD = 0.05  # 5%
    
    # 数据抓取年份范围（2020-2024，5年数据）
    YEAR_RANGE = [2020, 2021, 2022, 2023, 2024]
    
    # 模板文件名
    TEMPLATE_FILE = "2025年五年投资收益计算表-模版.xlsx"
    
    # 输出文件前缀
    OUTPUT_FILE_PREFIX = "2025年五年投资收益计算表-"
    
    # 爬虫请求间隔（秒）
    REQUEST_INTERVAL = 1.5

# ========== 数据降级策略 ==========
class FallbackStrategy:
    # 数据源优先级
    SOURCE_PRIORITY = [
        "eastmoney",  # 主数据源
        "yiniu",      # 备用数据源1
        "xueqiu"      # 备用数据源2
    ]
    
    # 重试策略
    RETRY_STRATEGY = {
        "max_retries": 3,
        "backoff_factor": 1.0,
        "retry_exceptions": [
            "ConnectionError",
            "TimeoutError",
            "HTTPError"
        ]
    }
    
    # 数据完整性检查阈值
    DATA_COMPLETENESS_THRESHOLD = 0.8  # 80%的数据字段必须有值

# ========== 日志配置 ==========
class LogConfig:
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = f"financial_spider_{time.strftime('%Y%m%d_%H%M%S')}.log"
