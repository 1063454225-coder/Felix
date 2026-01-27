# -*- coding: utf-8 -*-
"""
爬虫模块：实现多数据源的财报数据抓取，包含降级机制
"""

import requests
import pandas as pd
import numpy as np
import time
import random
from bs4 import BeautifulSoup
from config import SpiderConfig, Constants, FallbackStrategy
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinancialDataSpider:
    def __init__(self):
        self.session = requests.Session()
        self.request_interval = Constants.REQUEST_INTERVAL
    
    def get_random_user_agent(self):
        """获取随机User-Agent，避免被封IP"""
        user_agents = [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:120.0) Gecko/20100101 Firefox/120.0",
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            # Mobile devices
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 13; SM-G998U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 12; SM-G991U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36"
        ]
        return random.choice(user_agents)
    
    def make_request(self, url, headers=None, params=None, timeout=10, retry=3):
        """发送请求并处理重试逻辑"""
        if headers is None:
            headers = {}
        headers['User-Agent'] = self.get_random_user_agent()
        
        for i in range(retry):
            try:
                response = self.session.get(url, headers=headers, params=params, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {i+1}/{retry}): {e}")
                if i < retry - 1:
                    time.sleep(Constants.REQUEST_INTERVAL * (i + 1))
                else:
                    logger.error(f"All attempts failed: {e}")
                    raise
    
    def parse_eastmoney_financial_report(self, json_content, report_type):
        """解析东方财富的财务报表JSON数据"""
        try:
            import json
            
            # 解析JSON数据
            data = json.loads(json_content)
            
            # 检查数据结构
            if 'result' not in data:
                raise ValueError("数据结构不符合预期，缺少'result'字段")
            
            if 'data' not in data['result']:
                raise ValueError("数据结构不符合预期，缺少'result.data'字段")
            
            # 获取数据列表
            data_list = data['result']['data']
            if not data_list:
                raise ValueError("数据列表为空")
            
            # 转换为DataFrame
            df = pd.DataFrame(data_list)
            
            logger.info(f"JSON解析成功，获取到 {len(df)} 行数据")
            return df
        except Exception as e:
            logger.error(f"JSON解析失败: {e}")
            raise
    
    def get_eastmoney_financial_report(self, stock_code, report_type, years=None):
        """
        获取东方财富的财务报表数据
        :param stock_code: 股票代码，如 SH600519
        :param report_type: 报表类型，可选 'income' (利润表), 'balance' (资产负债表), 'cash_flow' (现金流量表)
        :param years: 年份列表，如 [2020, 2021, 2022, 2023, 2024]
        :return: 财务报表数据 DataFrame
        """
        if years is None:
            years = Constants.YEAR_RANGE
        
        # 提取股票代码数字部分（去掉SH/SZ前缀）
        stock_num = stock_code[2:] if stock_code.startswith('SH') or stock_code.startswith('SZ') else stock_code
        
        # 报表类型映射到东方财富的reportName
        report_name_map = {
            'income': 'RPT_LICO_FN_CPD',      # 利润表（合并报表）
            'balance': 'RPT_DMSK_FN_BALANCE',  # 资产负债表（合并报表）
            'cash_flow': 'RPT_DMSK_FN_CASHFLOW'  # 现金流量表（合并报表）
        }
        report_name = report_name_map.get(report_type)
        if not report_name:
            raise ValueError(f"不支持的报表类型: {report_type}")
        
        # 东方财富网财报数据API接口
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        
        # 根据报表类型设置不同的排序字段（某些报表可能不支持REPORTDATE排序）
        sort_column_map = {
            'income': 'REPORTDATE',      # 利润表使用报告日期
            'balance': 'REPORTDATE',     # 资产负债表使用报告日期
            'cash_flow': 'REPORTDATE'    # 现金流量表使用报告日期
        }
        sort_column = sort_column_map.get(report_type, 'REPORTDATE')
        
        # 设置请求参数
        params = {
            "pageSize": "50",             # 每页数据量
            "pageNumber": "1",            # 页码
            "columns": "ALL",             # 获取所有列
            "filter": f"(SECURITY_CODE=\"{stock_num}\")",  # 过滤条件：股票代码
            "reportName": report_name  # 报告名称
        }
        
        # 只有利润表使用排序，其他报表不使用排序（避免API错误）
        if report_type == 'income':
            params["sortColumns"] = sort_column
            params["sortTypes"] = "-1"
        
        # 参考文件中的请求头和cookies
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": f"https://data.eastmoney.com/bbsj/yjbb/{stock_num}.html",
            "Sec-Fetch-Dest": "script",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        
        logger.info(f"正在抓取东方财富 {report_type} 报表: {stock_code} - URL: {url}")
        
        # 发送请求
        response = self.make_request(url, headers=headers, params=params)
        
        # 先查看返回内容的前500个字符，了解实际格式
        logger.info(f"API返回内容: {response.text[:500]}...")
        
        try:
            # 解析JSONP格式的响应
            import re
            jsonp_match = re.search(r'jQuery\d+_\d+\((.*?)\);', response.text, re.S)
            if jsonp_match:
                json_content = jsonp_match.group(1)
            else:
                # 尝试直接作为JSON解析
                json_content = response.text
                
            # 解析JSON数据
            df = self.parse_eastmoney_financial_report(json_content, report_type)
            
            # 根据报表类型处理数据
            if report_type == 'income':
                # 利润表：筛选年报数据（DATATYPE包含'年报'）
                if 'DATATYPE' in df.columns:
                    df_annual = df[df['DATATYPE'].str.contains('年报')].copy()
                else:
                    df_annual = df.copy()
                
                # 从REPORTDATE提取年份并筛选所需年份
                df_annual['YEAR'] = pd.to_datetime(df_annual['REPORTDATE']).dt.year
                df_filtered = df_annual[df_annual['YEAR'].isin(years)]
                
                # 利润表需要的列（包含公司名称、EPS和营业成本）
                available_columns = ['SECURITY_CODE', 'YEAR']
                if 'REPORTDATE' in df.columns:
                    available_columns.append('REPORTDATE')
                if 'SECURITY_NAME_ABBR' in df.columns:
                    available_columns.append('SECURITY_NAME_ABBR')
                if 'TRADE_MARKET' in df.columns:
                    available_columns.append('TRADE_MARKET')
                if 'TOTAL_OPERATE_INCOME' in df.columns:
                    available_columns.append('TOTAL_OPERATE_INCOME')
                if 'TOTAL_OPERATE_COST' in df.columns:
                    available_columns.append('TOTAL_OPERATE_COST')
                if 'XSMLL' in df.columns:  # 销售毛利率
                    available_columns.append('XSMLL')
                if 'PARENT_NETPROFIT' in df.columns:
                    available_columns.append('PARENT_NETPROFIT')
                if 'WEIGHTAVG_ROE' in df.columns:
                    available_columns.append('WEIGHTAVG_ROE')
                if 'BASIC_EPS' in df.columns:
                    available_columns.append('BASIC_EPS')
                
                df_filtered = df_filtered[available_columns]
                
            elif report_type == 'balance':
                # 资产负债表：使用REPORT_DATE字段
                if 'REPORT_DATE' in df.columns:
                    df['YEAR'] = pd.to_datetime(df['REPORT_DATE']).dt.year
                elif 'REPORTDATE' in df.columns:
                    df['YEAR'] = pd.to_datetime(df['REPORTDATE']).dt.year
                else:
                    raise ValueError("资产负债表数据中缺少REPORT_DATE或REPORTDATE字段")
                
                df_filtered = df[df['YEAR'].isin(years)].copy()
                
                # 资产负债表需要的列（包含总权益、负债合计和资产合计）
                available_columns = ['SECURITY_CODE', 'YEAR']
                if 'REPORT_DATE' in df.columns:
                    available_columns.append('REPORT_DATE')
                elif 'REPORTDATE' in df.columns:
                    available_columns.append('REPORTDATE')
                
                # 添加行业信息、总权益、负债合计和资产合计字段
                if 'INDUSTRY_NAME' in df.columns:
                    available_columns.append('INDUSTRY_NAME')
                if 'TOTAL_EQUITY' in df.columns:
                    available_columns.append('TOTAL_EQUITY')
                if 'TOTAL_LIABILITIES' in df.columns:
                    available_columns.append('TOTAL_LIABILITIES')
                if 'TOTAL_ASSETS' in df.columns:
                    available_columns.append('TOTAL_ASSETS')
                if 'SECURITY_NAME_ABBR' in df.columns:
                    available_columns.append('SECURITY_NAME_ABBR')
                
                df_filtered = df_filtered[available_columns]
                
            elif report_type == 'cash_flow':
                # 现金流量表：使用REPORT_DATE字段
                if 'REPORT_DATE' in df.columns:
                    df['YEAR'] = pd.to_datetime(df['REPORT_DATE']).dt.year
                elif 'REPORTDATE' in df.columns:
                    df['YEAR'] = pd.to_datetime(df['REPORTDATE']).dt.year
                else:
                    raise ValueError("现金流量表数据中缺少REPORT_DATE或REPORTDATE字段")
                
                df_filtered = df[df['YEAR'].isin(years)].copy()
                
                # 现金流量表需要的列（包含经营活动产生的现金流量净额）
                available_columns = ['SECURITY_CODE', 'YEAR']
                if 'REPORT_DATE' in df.columns:
                    available_columns.append('REPORT_DATE')
                elif 'REPORTDATE' in df.columns:
                    available_columns.append('REPORTDATE')
                
                # 添加经营活动产生的现金流量净额字段
                if 'OPERATING_CASH_FLOW' in df.columns:
                    available_columns.append('OPERATING_CASH_FLOW')
                if 'N_CASH_FLOWS_FROM_OPERATING_A' in df.columns:
                    available_columns.append('N_CASH_FLOWS_FROM_OPERATING_A')
                if 'NETCASH_OPERATE' in df.columns:  # 经营活动产生的现金流量净额
                    available_columns.append('NETCASH_OPERATE')
                if 'CASH_PAID_FOR_DIVIDENDS_PROFITS_INTEREST' in df.columns:
                    available_columns.append('CASH_PAID_FOR_DIVIDENDS_PROFITS_INTEREST')
                if 'CASH_PAID_FOR_DIVIDENDS_AND_INTEREST' in df.columns:
                    available_columns.append('CASH_PAID_FOR_DIVIDENDS_AND_INTEREST')
                if 'N_CASH_FLOWS_FROM_FINANCING_A' in df.columns:
                    available_columns.append('N_CASH_FLOWS_FROM_FINANCING_A')
                
                df_filtered = df_filtered[available_columns]
            
            # 获取实际筛选到的年份列表
            actual_years = sorted(df_filtered['YEAR'].unique())
            logger.info(f"成功获取东方财富 {report_type} 报表: {stock_code}，年份: {actual_years}")
            return df_filtered
        except Exception as e:
            logger.error(f"解析失败: {e}")
            # 保存响应内容到文件以便分析
            try:
                with open(f"eastmoney_{stock_code}_{report_type}.json", "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info(f"响应内容已保存到文件: eastmoney_{stock_code}_{report_type}.json")
            except Exception as e2:
                logger.error(f"保存响应内容失败: {e2}")
            raise
    
    def get_eastmoney_company_info(self, stock_code):
        """获取东方财富的公司基本信息"""
        try:
            # 先从财务报表中提取公司信息
            income_data = self.get_eastmoney_financial_report(stock_code, 'income', years=[2024])
            balance_data = self.get_eastmoney_financial_report(stock_code, 'balance', years=[2024])
            
            company_info = {
                'SECURITY_CODE': stock_code,
                'SECURITY_NAME_ABBR': '',
                'INDUSTRY': '',
                'TRADE_MARKET': ''
            }
            
            # 从利润表获取公司名称
            if income_data is not None and not income_data.empty:
                first_row = income_data.iloc[0]
                company_info['SECURITY_NAME_ABBR'] = first_row.get('SECURITY_NAME_ABBR', '')
                company_info['TRADE_MARKET'] = first_row.get('TRADE_MARKET', '')
                logger.info(f"从利润表获取公司名称: {company_info['SECURITY_NAME_ABBR']}")
            
            # 从资产负债表获取行业信息和公司名称（如果利润表中没有的话）
            if balance_data is not None and not balance_data.empty:
                first_row = balance_data.iloc[0]
                # 优先使用INDUSTRY_NAME，如果不存在则使用TRADE_MARKET
                industry = first_row.get('INDUSTRY_NAME', '') or first_row.get('TRADE_MARKET', '')
                company_info['INDUSTRY'] = industry
                logger.info(f"从资产负债表获取行业信息: {industry}")
                
                # 如果利润表中没有公司名称，从资产负债表获取
                if not company_info['SECURITY_NAME_ABBR']:
                    company_info['SECURITY_NAME_ABBR'] = first_row.get('SECURITY_NAME_ABBR', '')
                    logger.info(f"从资产负债表获取公司名称: {company_info['SECURITY_NAME_ABBR']}")
            
            logger.info(f"从财务报表中提取公司信息: {company_info.get('SECURITY_NAME_ABBR', '')}, 行业: {company_info.get('INDUSTRY', '')}")
            return company_info
            
        except Exception as e:
            logger.warning(f"获取公司信息失败: {e}")
            return {
                'SECURITY_CODE': stock_code,
                'SECURITY_NAME_ABBR': '',
                'INDUSTRY': '',
                'TRADE_MARKET': ''
            }
    
    def get_eastmoney_share_capital(self, stock_code):
        """获取东方财富的总股本信息"""
        # 构建URL，使用CompanySurvey接口
        # 注意：东方财富的接口可能需要不同的股票代码格式
        if stock_code.startswith('SH'):
            api_code = stock_code
        elif stock_code.startswith('SZ'):
            api_code = stock_code
        else:
            # 如果股票代码格式不正确，直接返回0
            logger.error(f"股票代码格式不正确: {stock_code}")
            return 0
        
        url = f"https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax?code={api_code}"
        
        logger.info(f"\n正在抓取东方财富总股本数据: {stock_code}")
        logger.info(f"API URL: {url}")
        
        try:
            # 发送请求
            response = self.make_request(url, headers=SpiderConfig.EASTMONEY['headers'])
            logger.info(f"API响应状态码: {response.status_code}")
            
            # 检查响应状态
            if response.status_code != 200:
                logger.error(f"API请求失败，状态码: {response.status_code}")
                return 0
            
            # 解析响应内容
            response_text = response.text
            logger.info(f"API响应内容: {response_text}")
            
            # 检查响应内容是否为空
            if not response_text:
                logger.error("API响应内容为空")
                return 0
            
            # 解析JSON数据
            try:
                data = response.json()
                logger.info(f"API响应解析: {data}")
            except Exception as json_error:
                logger.error(f"解析JSON数据失败: {json_error}")
                return 0
            
            # 检查数据是否存在
            if not isinstance(data, dict):
                logger.error(f"API响应数据格式不正确: {type(data)}")
                return 0
            
            # 检查jbzl字段
            if 'jbzl' not in data:
                logger.error("响应中没有jbzl字段")
                # 尝试获取其他可能的字段
                for key, value in data.items():
                    logger.info(f"响应字段: {key} = {value}")
                return 0
            
            jbzl_data = data['jbzl']
            logger.info(f"jbzl数据: {jbzl_data}")
            
            # 处理jbzl_data是列表的情况
            if isinstance(jbzl_data, list):
                if not jbzl_data:
                    logger.error("jbzl数据列表为空")
                    return 0
                # 取列表中的第一个元素
                jbzl_data = jbzl_data[0]
                logger.info(f"jbzl数据(列表第一个元素): {jbzl_data}")
            
            # 检查zgb字段
            if 'zgb' in jbzl_data:
                zgb_value = jbzl_data['zgb']
                logger.info(f"zgb值: {zgb_value}")
            elif 'REG_CAPITAL' in jbzl_data:
                # 如果没有zgb字段，尝试使用REG_CAPITAL字段
                zgb_value = jbzl_data['REG_CAPITAL']
                logger.info(f"使用REG_CAPITAL作为总股本: {zgb_value}")
            else:
                logger.error("jbzl数据中没有zgb或REG_CAPITAL字段")
                # 尝试获取其他可能的总股本字段
                if isinstance(jbzl_data, dict):
                    for key, value in jbzl_data.items():
                        logger.info(f"jbzl字段: {key} = {value}")
                return 0
            
            # 处理不同单位的情况
            import re
            
            # 如果zgb_value已经是数字类型，直接使用
            if isinstance(zgb_value, (int, float)):
                # 假设REG_CAPITAL的单位是万股
                total_shares = zgb_value * 1e4
                logger.info(f"成功获取总股本数据: {total_shares}股")
                return total_shares
            
            # 如果是字符串类型，需要解析
            # 匹配数字部分和单位部分
            match = re.match(r'([\d.]+)(亿|万)?', zgb_value)
            if not match:
                logger.error(f"无法匹配zgb值格式: {zgb_value}")
                return 0
            
            num_str = match.group(1)
            unit = match.group(2)
            
            try:
                num = float(num_str)
                # 根据单位转换为股数
                if unit == '亿':
                    total_shares = num * 1e8
                elif unit == '万':
                    total_shares = num * 1e4
                else:
                    # 没有单位，直接使用数字
                    total_shares = num
                
                logger.info(f"成功获取总股本数据: {total_shares}股")
                return total_shares
            except ValueError:
                logger.error(f"无法解析zgb值: {zgb_value}")
                return 0
        except Exception as e:
            logger.error(f"获取总股本数据失败: {e}")
            import traceback
            traceback.print_exc()
            # 返回0而不是抛出异常，让上层代码处理默认值
            return 0
    
    def get_eastmoney_valuation(self, stock_code):
        """获取东方财富的估值数据（PE/PB等）"""
        # 转换股票代码格式：市场代码.股票代码
        # 1 = 上海证券交易所(SH), 0 = 深圳证券交易所(SZ)
        if stock_code.startswith('SH'):
            market_code = '1'
            stock_num = stock_code[2:]
        elif stock_code.startswith('SZ'):
            market_code = '0'
            stock_num = stock_code[2:]
        else:
            raise ValueError("股票代码格式错误，应为 SHXXX 或 SZXXX")
        
        secid = f"{market_code}.{stock_num}"
        
        # 构建URL
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f44,f45,f60,f62,f169,f170,f116"
        
        logger.info(f"正在抓取东方财富估值数据: {stock_code} (secid={secid})")
        logger.info(f"API URL: {url}")
        
        try:
            response = self.make_request(url, headers=SpiderConfig.EASTMONEY['headers'])
            logger.info(f"API响应状态码: {response.status_code}")
            logger.info(f"API响应内容: {response.text}")
            
            data = response.json()
            logger.info(f"API响应解析: {data}")
            
            # 检查数据是否存在
            if 'data' in data and data['data']:
                raw_data = data['data']
                logger.info(f"原始数据: {raw_data}")
                
                # 获取当前价格
                f43_value = raw_data.get('f43', 0) or 0
                current_price = f43_value / 100  # 当前价格（分→元）
                logger.info(f"f43值: {f43_value}, 当前价格: {current_price}元")
                
                # 获取总市值
                f116_value = raw_data.get('f116', 0) or 0
                total_market_cap = f116_value / 100000000  # 总市值（分→元→亿元）
                logger.info(f"f116值: {f116_value}, 总市值: {total_market_cap}亿元")
                
                # 尝试从财务报表中获取EPS和BPS来计算PE和PB
                pe_ttm = 0
                pb = 0
                eps = 0
                
                try:
                    # 获取最新的财务数据
                    income_data = self.get_eastmoney_financial_report(stock_code, 'income', years=[2024])
                    balance_data = self.get_eastmoney_financial_report(stock_code, 'balance', years=[2024])
                    
                    if income_data is not None and not income_data.empty:
                        latest_income = income_data.iloc[0]
                        logger.info(f"利润表最新行数据: {dict(latest_income)}")
                        eps = latest_income.get('BASIC_EPS', 0) or 0  # 每股收益
                        logger.info(f"从利润表获取EPS: {eps}, 类型: {type(eps)}")
                        if eps > 0 and current_price > 0:
                            pe_ttm = current_price / eps
                            logger.info(f"计算PE: {current_price} / {eps} = {pe_ttm}")
                    
                    if balance_data is not None and not balance_data.empty:
                        latest_balance = balance_data.iloc[0]
                        logger.info(f"资产负债表最新行数据: {dict(latest_balance)}")
                        # 检查是否有BPS字段，如果没有则使用其他方式计算
                        bps = latest_balance.get('BPS', 0) or 0  # 每股净资产
                        if bps == 0:
                            # 如果没有BPS字段，尝试从总权益和总股本计算
                            total_equity = latest_balance.get('TOTAL_EQUITY', 0) or 0
                            logger.info(f"从资产负债表获取TOTAL_EQUITY: {total_equity}")
                            # 动态获取总股本
                            total_shares = self.get_eastmoney_share_capital(stock_code)
                            logger.info(f"使用动态获取的总股本: {total_shares}股")
                            if total_equity > 0 and total_shares > 0:
                                bps = total_equity / total_shares
                                logger.info(f"从总权益计算BPS: {total_equity} / {total_shares} = {bps}")
                        
                        logger.info(f"从资产负债表获取BPS: {bps}, 类型: {type(bps)}")
                        if bps > 0 and current_price > 0:
                            pb = current_price / bps
                            logger.info(f"计算PB: {current_price} / {bps} = {pb}")
                    
                except Exception as calc_error:
                    logger.warning(f"计算PE/PB失败: {calc_error}")
                    import traceback
                    traceback.print_exc()
                
                valuation_data = {
                    'current_price': current_price,
                    'pe_ttm': pe_ttm,
                    'pb': pb,
                    'total_market_cap': total_market_cap,
                    'eps': eps  # 使用从财务报表中获取的EPS
                }
                logger.info(f"成功获取估值数据: 股价={valuation_data['current_price']}元, 市值={valuation_data['total_market_cap']}亿元, PE={valuation_data['pe_ttm']}, PB={valuation_data['pb']}, EPS={valuation_data['eps']}")
                return valuation_data
            else:
                # 如果没有数据，返回默认值
                logger.warning("未获取到估值数据，返回默认值")
                return {
                    'current_price': 0,
                    'pe_ttm': 0,
                    'pb': 0,
                    'total_market_cap': 0,
                    'eps': 0
                }
        except Exception as e:
            logger.error(f"获取估值数据失败: {e}")
            import traceback
            traceback.print_exc()
            # 返回默认值而不是抛出异常
            return {
                'current_price': 0,
                'pe_ttm': 0,
                'pb': 0,
                'total_market_cap': 0,
                'eps': 0
            }
    
    def get_financial_data(self, stock_code, report_type, years=None):
        """
        获取财务数据的主函数，包含降级机制
        :param stock_code: 股票代码
        :param report_type: 报表类型
        :param years: 年份列表
        :return: 财务报表数据
        """
        if years is None:
            years = Constants.YEAR_RANGE
        
        data = None
        
        # 按照数据源优先级尝试获取数据
        for source in FallbackStrategy.SOURCE_PRIORITY:
            try:
                if source == 'eastmoney':
                    data = self.get_eastmoney_financial_report(stock_code, report_type, years)
                    break
                # 后续可以添加其他数据源的支持
                elif source == 'yiniu':
                    # data = self.get_yiniu_financial_report(stock_code, report_type, years)
                    # break
                    continue
                elif source == 'xueqiu':
                    # data = self.get_xueqiu_financial_report(stock_code, report_type, years)
                    # break
                    continue
            except Exception as e:
                logger.warning(f"{source}数据源获取失败: {e}，尝试下一个数据源")
        
        if data is None:
            raise ValueError(f"所有数据源均获取失败: {stock_code} - {report_type}")
        
        return data
    
    def get_company_financial_data(self, stock_code, years=None):
        """
        获取公司的完整财务数据（三大报表）
        :param stock_code: 股票代码
        :param years: 年份列表
        :return: 包含所有财务数据的字典
        """
        if years is None:
            years = Constants.YEAR_RANGE
        
        logger.info(f"开始获取 {stock_code} 的完整财务数据...")
        
        try:
            # 获取三大报表
            income_statement = self.get_financial_data(stock_code, 'income', years)
            balance_sheet = self.get_financial_data(stock_code, 'balance', years)
            cash_flow_statement = self.get_financial_data(stock_code, 'cash_flow', years)
            
            # 检查是否缺少2025年数据，如果缺少则添加预测数据
            if 2025 in years:
                income_statement = self._add_forecast_data(stock_code, income_statement, 'income', 2025)
                balance_sheet = self._add_forecast_data(stock_code, balance_sheet, 'balance', 2025)
                cash_flow_statement = self._add_forecast_data(stock_code, cash_flow_statement, 'cash_flow', 2025)
            
            # 获取公司信息
            company_info = self.get_eastmoney_company_info(stock_code)
            
            # 获取主要财务指标数据（失败不影响整体流程）
            key_indicators = pd.DataFrame()
            try:
                key_indicators = self.get_eastmoney_key_indicators(stock_code, years)
                logger.info("成功获取主要财务指标数据")
            except Exception as e:
                logger.warning(f"获取主要财务指标数据失败，将使用默认值: {e}")
                key_indicators = pd.DataFrame()
            
            # 获取估值数据（失败不影响整体流程）
            valuation_data = {}
            try:
                valuation_data = self.get_eastmoney_valuation(stock_code)
                logger.info("成功获取估值数据")
            except Exception as e:
                logger.warning(f"获取估值数据失败，将使用默认值: {e}")
                valuation_data = {
                    'current_price': 0,
                    'pe_ttm': 0,
                    'pb': 0,
                    'total_market_cap': 0,
                    'eps': 0
                }
            
            # 获取总股本数据（失败不影响整体流程）
            share_capital = 0
            try:
                logger.info(f"开始获取总股本数据: {stock_code}")
                share_capital = self.get_eastmoney_share_capital(stock_code)
                logger.info(f"成功获取总股本数据: {share_capital}股")
                
                # 验证总股本数据是否合理（至少1亿股）
                if share_capital < 1e8:
                    logger.warning(f"获取到的总股本数据不合理: {share_capital}股，将使用默认值")
                    share_capital = 0.0
            except Exception as e:
                logger.warning(f"获取总股本数据失败，将使用默认值: {e}")
                import traceback
                traceback.print_exc()
                share_capital = 0.0
            
            logger.info(f"成功获取 {stock_code} 的完整财务数据")
            
            return {
                'income_statement': income_statement,
                'balance_sheet': balance_sheet,
                'cash_flow_statement': cash_flow_statement,
                'key_indicators': key_indicators,
                'company_info': company_info,
                'valuation_data': valuation_data,
                'share_capital': share_capital
            }
        except Exception as e:
            logger.error(f"获取完整财务数据失败: {e}")
            raise
    
    def _add_forecast_data(self, stock_code, df, report_type, year):
        """
        添加预测数据到DataFrame
        :param stock_code: 股票代码
        :param df: 原始DataFrame
        :param report_type: 报表类型
        :param year: 预测年份
        :return: 包含预测数据的DataFrame
        """
        # 检查是否已存在该年份的数据
        if 'YEAR' in df.columns and year in df['YEAR'].values:
            logger.info(f"{year}年数据已存在，无需添加预测数据")
            return df
        
        logger.info(f"为{stock_code}添加{year}年{report_type}预测数据...")
        
        # 尝试从雪球或亿牛网获取预测数据
        forecast_data = None
        for source in ['xueqiu', 'yiniu']:
            try:
                forecast_data = self._get_forecast_from_source(stock_code, report_type, year, source)
                if forecast_data:
                    break
            except Exception as e:
                logger.warning(f"从{source}获取{year}年预测数据失败: {e}")
                continue
        
        # 如果无法获取预测数据，则基于历史数据生成简单预测
        if forecast_data is None:
            forecast_data = self._generate_simple_forecast(df, report_type, year)
            logger.info(f"基于历史数据生成{year}年预测数据")
        
        # 将预测数据添加到DataFrame
        if forecast_data:
            forecast_row = pd.DataFrame([forecast_data])
            df_with_forecast = pd.concat([df, forecast_row], ignore_index=True)
            return df_with_forecast
        else:
            logger.warning(f"无法为{year}年生成预测数据")
            return df
    
    def _get_forecast_from_source(self, stock_code, report_type, year, source):
        """
        从雪球或亿牛网获取预测数据
        :param stock_code: 股票代码
        :param report_type: 报表类型
        :param year: 预测年份
        :param source: 数据源
        :return: 预测数据字典
        """
        # 这里可以实现具体的预测数据抓取逻辑
        # 目前先返回None，后续可以扩展
        return None
    
    def get_eastmoney_key_indicators(self, stock_code, years=None):
        """
        获取东方财富的主要财务指标数据
        :param stock_code: 股票代码，如 SH600519
        :param years: 年份列表，如 [2020, 2021, 2022, 2023, 2024]
        :return: 主要财务指标数据 DataFrame
        """
        if years is None:
            years = Constants.YEAR_RANGE
        
        # 提取股票代码数字部分（去掉SH/SZ前缀）
        stock_num = stock_code[2:] if stock_code.startswith('SH') or stock_code.startswith('SZ') else stock_code
        
        # 东方财富网主要财务指标API接口
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        
        # 设置请求参数
        params = {
            "pageSize": "50",             # 每页数据量
            "pageNumber": "1",            # 页码
            "columns": "ALL",             # 获取所有列
            "filter": f"(SECURITY_CODE='{stock_num}')",  # 过滤条件：股票代码
            "reportName": "RPT_F10_MAINFINANCIALINDICATOR",  # 主要财务指标
            "sortColumns": "REPORTDATE",  # 按报告日期排序
            "sortTypes": "-1"             # 降序排列
        }
        
        # 参考文件中的请求头
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": f"https://data.eastmoney.com/bbsj/yjbb/{stock_num}.html",
            "Sec-Fetch-Dest": "script",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        
        logger.info(f"正在抓取东方财富主要财务指标: {stock_code} - URL: {url}")
        
        try:
            # 发送请求
            response = self.make_request(url, headers=headers, params=params)
            
            # 先查看返回内容的前500个字符，了解实际格式
            logger.info(f"API返回内容: {response.text[:500]}...")
            
            # 解析JSONP格式的响应
            import re
            jsonp_match = re.search(r'jQuery\d+_\d+\((.*?)\);', response.text, re.S)
            if jsonp_match:
                json_content = jsonp_match.group(1)
            else:
                # 尝试直接作为JSON解析
                json_content = response.text
                
            # 解析JSON数据
            df = self.parse_eastmoney_financial_report(json_content, 'key_indicators')
            
            # 筛选年报数据（DATATYPE包含'年报'）
            if 'DATATYPE' in df.columns:
                df_annual = df[df['DATATYPE'].str.contains('年报')].copy()
            else:
                df_annual = df.copy()
            
            # 从REPORTDATE提取年份并筛选所需年份
            if 'REPORTDATE' in df.columns:
                df_annual['YEAR'] = pd.to_datetime(df_annual['REPORTDATE']).dt.year
                df_filtered = df_annual[df_annual['YEAR'].isin(years)]
            else:
                # 如果没有REPORTDATE列，返回空DataFrame
                logger.warning("主要财务指标数据中缺少REPORTDATE字段")
                return pd.DataFrame()
            
            # 获取实际筛选到的年份列表
            actual_years = sorted(df_filtered['YEAR'].unique())
            logger.info(f"成功获取东方财富主要财务指标: {stock_code}，年份: {actual_years}")
            return df_filtered
        except Exception as e:
            logger.error(f"获取主要财务指标失败: {e}")
            # 保存响应内容到文件以便分析
            try:
                with open(f"eastmoney_{stock_code}_key_indicators.json", "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info(f"响应内容已保存到文件: eastmoney_{stock_code}_key_indicators.json")
            except Exception as e2:
                logger.error(f"保存响应内容失败: {e2}")
            # 返回空DataFrame而不是抛出异常
            return pd.DataFrame()
    
    def _generate_simple_forecast(self, df, report_type, year):
        """
        基于历史数据生成简单预测
        :param df: 历史数据DataFrame
        :param report_type: 报表类型
        :param year: 预测年份
        :return: 预测数据字典
        """
        if df.empty or 'YEAR' not in df.columns:
            return None
        
        # 获取最近3年的数据
        recent_years = sorted(df['YEAR'].unique())[-3:]
        recent_data = df[df['YEAR'].isin(recent_years)]
        
        if recent_data.empty:
            return None
        
        # 计算平均增长率
        forecast_row = {
            'SECURITY_CODE': df.iloc[0]['SECURITY_CODE'] if 'SECURITY_CODE' in df.columns else '',
            'REPORTDATE': f'{year}-12-31 00:00:00',
            'DATATYPE': '预测数据',
            'YEAR': year
        }
        
        # 根据报表类型设置预测值
        if report_type == 'income':
            # 利润表预测
            if 'TOTAL_OPERATE_INCOME' in df.columns and not recent_data['TOTAL_OPERATE_INCOME'].isna().all():
                valid_revenue = recent_data['TOTAL_OPERATE_INCOME'].dropna()
                if len(valid_revenue) >= 2:
                    avg_revenue_growth = valid_revenue.pct_change().mean()
                    last_revenue = valid_revenue.iloc[-1]
                    forecast_row['TOTAL_OPERATE_INCOME'] = last_revenue * (1 + avg_revenue_growth) if pd.notna(avg_revenue_growth) and avg_revenue_growth > -0.5 else last_revenue * 1.1
            
            if 'PARENT_NETPROFIT' in df.columns and not recent_data['PARENT_NETPROFIT'].isna().all():
                valid_profit = recent_data['PARENT_NETPROFIT'].dropna()
                if len(valid_profit) >= 2:
                    avg_profit_growth = valid_profit.pct_change().mean()
                    last_profit = valid_profit.iloc[-1]
                    forecast_row['PARENT_NETPROFIT'] = last_profit * (1 + avg_profit_growth) if pd.notna(avg_profit_growth) and avg_profit_growth > -0.5 else last_profit * 1.1
            
            if 'WEIGHTAVG_ROE' in df.columns and not recent_data['WEIGHTAVG_ROE'].isna().all():
                valid_roe = recent_data['WEIGHTAVG_ROE'].dropna()
                if len(valid_roe) > 0:
                    avg_roe = valid_roe.mean()
                    forecast_row['WEIGHTAVG_ROE'] = avg_roe if pd.notna(avg_roe) else 15.0
        
        elif report_type == 'balance':
            # 资产负债表预测
            if 'TOTAL_ASSETS' in df.columns and not recent_data['TOTAL_ASSETS'].isna().all():
                valid_assets = recent_data['TOTAL_ASSETS'].dropna()
                if len(valid_assets) >= 2:
                    avg_asset_growth = valid_assets.pct_change().mean()
                    last_assets = valid_assets.iloc[-1]
                    forecast_row['TOTAL_ASSETS'] = last_assets * (1 + avg_asset_growth) if pd.notna(avg_asset_growth) and avg_asset_growth > -0.5 else last_assets * 1.08
            
            if 'TOTAL_LIABILITIES' in df.columns and not recent_data['TOTAL_LIABILITIES'].isna().all():
                valid_liabilities = recent_data['TOTAL_LIABILITIES'].dropna()
                if len(valid_liabilities) >= 2:
                    avg_liability_growth = valid_liabilities.pct_change().mean()
                    last_liabilities = valid_liabilities.iloc[-1]
                    forecast_row['TOTAL_LIABILITIES'] = last_liabilities * (1 + avg_liability_growth) if pd.notna(avg_liability_growth) and avg_liability_growth > -0.5 else last_liabilities * 1.08
            
            # 计算资产负债率
            if 'TOTAL_ASSETS' in forecast_row and 'TOTAL_LIABILITIES' in forecast_row:
                if forecast_row['TOTAL_ASSETS'] > 0:
                    forecast_row['ASSET_LIABILITY_RATIO'] = forecast_row['TOTAL_LIABILITIES'] / forecast_row['TOTAL_ASSETS']
                else:
                    forecast_row['ASSET_LIABILITY_RATIO'] = 0.5
        
        elif report_type == 'cash_flow':
            # 现金流量表预测
            if 'OPERATING_CASH_FLOW' in df.columns and not recent_data['OPERATING_CASH_FLOW'].isna().all():
                valid_cash_flow = recent_data['OPERATING_CASH_FLOW'].dropna()
                if len(valid_cash_flow) >= 2:
                    avg_cash_flow_growth = valid_cash_flow.pct_change().mean()
                    last_cash_flow = valid_cash_flow.iloc[-1]
                    forecast_row['OPERATING_CASH_FLOW'] = last_cash_flow * (1 + avg_cash_flow_growth) if pd.notna(avg_cash_flow_growth) and avg_cash_flow_growth > -0.5 else last_cash_flow * 1.1
        
        return forecast_row

if __name__ == "__main__":
    # 测试爬虫
    spider = FinancialDataSpider()
    try:
        # 测试获取贵州茅台的利润表
        stock_code = 'SH600519'  # 贵州茅台
        income_data = spider.get_eastmoney_financial_report(stock_code, 'income', [2020, 2021, 2022, 2023, 2024])
        print(f"\n贵州茅台利润表数据 (2020-2024):")
        print(income_data.head(10))
        
        # 测试获取完整财务数据
        # full_data = spider.get_company_financial_data(stock_code)
        # print(f"\n完整财务数据获取成功")
        # print(f"利润表形状: {full_data['income_statement'].shape}")
        # print(f"资产负债表形状: {full_data['balance_sheet'].shape}")
        # print(f"现金流量表形状: {full_data['cash_flow_statement'].shape}")
    except Exception as e:
        print(f"测试失败: {e}")
