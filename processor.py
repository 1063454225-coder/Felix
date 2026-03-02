# -*- coding: utf-8 -*-
"""
数据处理模块：实现数据清洗、单位转换、指标计算和审计校验
"""

import pandas as pd
import numpy as np
from config import Constants, FieldMapping
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        self.unit_conversion = Constants.UNIT_CONVERSION
        self.decimal_places = Constants.DECIMAL_PLACES
        self.error_values = Constants.ERROR_VALUES
        self.audit_threshold = Constants.AUDIT_THRESHOLD
        
    def clean_value(self, val, indicator_config=None):
        """
        数据清洗函数：处理单位换算和空值填充
        :param val: 原始值
        :param indicator_config: 指标配置（包含单位、小数位数等信息）
        :return: 清洗后的值
        """
        # 处理异常值
        if val is None or val == "" or str(val).strip() in ["--", "N/A", "NA", "null", "None"]:
            return 0.0
        
        # 转换为数值
        try:
            if isinstance(val, str):
                val = float(val)
        except (ValueError, TypeError):
            logger.warning(f"无法转换值为数值: {val}")
            return 0.0
        
        # 如果没有提供配置，直接返回
        if indicator_config is None:
            return val
        
        # 处理NaN值
        if pd.isna(val):
            return 0.0
        
        # 单位换算
        if "conversion_factor" in indicator_config:
            val = val / indicator_config["conversion_factor"]
        
        # 保留小数位数
        decimal_places = indicator_config.get("decimal_places", 2)
        val = round(val, decimal_places)
        
        # 处理百分比格式
        if indicator_config.get("display_format") == "percentage":
            val = val / 100.0  # 转换为小数形式，Excel中配合%格式显示
        
        return val
        
    def convert_unit(self, value, conversion_type="ten_thousand_to_hundred_million"):
        """
        单位转换
        :param value: 原始值
        :param conversion_type: 转换类型
        :return: 转换后的值
        """
        if pd.isna(value) or value is None:
            return self.error_values["missing_data"]
            
        try:
            coefficient = self.unit_conversion.get(conversion_type, 1.0)
            converted_value = float(value) * coefficient
            return round(converted_value, self.decimal_places)
        except (ValueError, TypeError):
            logger.warning(f"单位转换失败，值: {value}, 转换类型: {conversion_type}")
            return self.error_values["invalid_value"]
    
    def calculate_growth_rate(self, current_value, previous_value, is_percentage=True):
        """
        计算增长率
        :param current_value: 当前值
        :param previous_value: 前一年值
        :param is_percentage: 是否返回百分比形式
        :return: 增长率
        """
        try:
            # 处理None和NaN值
            if current_value is None or pd.isna(current_value) or previous_value is None or pd.isna(previous_value):
                logger.warning(f"增长率计算遇到空值，当前值: {current_value}, 前一年值: {previous_value}")
                return self.error_values["missing_data"]
            
            current = float(current_value)
            previous = float(previous_value)
            
            # 处理零值和负值情况
            if previous == 0:
                if current == 0:
                    return 0.0
                else:
                    logger.warning(f"前一年值为0，无法计算增长率，当前值: {current}")
                    return self.error_values["divide_by_zero"]
            
            # 计算增长率，处理负值转折
            growth_rate = (current - previous) / abs(previous)
            
            # 限制增长率在合理范围内（-100%到+1000%）
            if growth_rate < -1.0:
                growth_rate = -1.0
            elif growth_rate > 10.0:
                growth_rate = 10.0
            
            if is_percentage:
                growth_rate *= 100
                return round(growth_rate, self.decimal_places)
            else:
                return round(growth_rate, self.decimal_places + 2)
        except (ValueError, TypeError, ZeroDivisionError) as e:
            logger.warning(f"增长率计算失败，当前值: {current_value}, 前一年值: {previous_value}, 错误: {e}")
            return self.error_values["invalid_value"]
    
    def process_income_statement(self, income_data, years=None):
        """
        处理利润表数据
        :param income_data: 利润表原始数据
        :param years: 需要处理的年份列表
        :return: 处理后的利润表数据
        """
        if years is None:
            years = Constants.YEAR_RANGE
            
        processed_data = {}
        
        try:
            # 检查数据格式，处理模拟数据和爬虫数据的差异
            if isinstance(income_data, pd.DataFrame) and 'YEAR' in income_data.columns:
                # 爬虫获取的数据格式
                # 按年份分组
                for year in years:
                    year_data = income_data[income_data['YEAR'] == year]
                    if not year_data.empty:
                        row = year_data.iloc[0]
                        
                        # 处理主营业务收入（万元转亿元）
                        revenue = self.convert_unit(row.get('TOTAL_OPERATE_INCOME', 0))
                        
                        # 处理净利润（万元转亿元）
                        net_profit = self.convert_unit(row.get('PARENT_NETPROFIT', 0))
                        
                        processed_data[year] = {
                            'revenue': revenue,
                            'net_profit': net_profit,
                        }
            elif isinstance(income_data, pd.DataFrame):
                # 模拟数据格式（行是指标，列是年份）
                for year in years:
                    if year in income_data.columns:
                        processed_data[year] = {
                            'revenue': self.convert_unit(income_data.loc['营业收入', year]),
                            'net_profit': self.convert_unit(income_data.loc['净利润', year]),
                        }
            
            # 计算各年增长率
            sorted_years = sorted(years)
            for i in range(1, len(sorted_years)):
                current_year = sorted_years[i]
                previous_year = sorted_years[i-1]
                
                if current_year in processed_data and previous_year in processed_data:
                    # 计算收入增长率
                    processed_data[current_year]['revenue_growth_rate'] = self.calculate_growth_rate(
                        processed_data[current_year]['revenue'],
                        processed_data[previous_year]['revenue']
                    )
                    
                    # 计算净利润增长率
                    processed_data[current_year]['net_profit_growth_rate'] = self.calculate_growth_rate(
                        processed_data[current_year]['net_profit'],
                        processed_data[previous_year]['net_profit']
                    )
            
            logger.info("利润表数据处理完成")
            return processed_data
            
        except Exception as e:
            logger.error(f"利润表数据处理失败: {e}")
            return processed_data
    
    def process_balance_sheet(self, balance_data, years=None):
        """
        处理资产负债表数据
        :param balance_data: 资产负债表原始数据
        :param years: 需要处理的年份列表
        :return: 处理后的资产负债表数据
        """
        if years is None:
            years = Constants.YEAR_RANGE
            
        processed_data = {}
        
        try:
            # 检查数据格式，处理模拟数据和爬虫数据的差异
            if isinstance(balance_data, pd.DataFrame) and 'YEAR' in balance_data.columns:
                # 爬虫获取的数据格式
                # 按年份分组
                for year in years:
                    year_data = balance_data[balance_data['YEAR'] == year]
                    if not year_data.empty:
                        row = year_data.iloc[0]
                        
                        # 处理资产负债率（如果有数据的话，百分比转小数）
                        asset_liability_ratio = self.convert_unit(
                            row.get('ASSET_LIABILITY_RATIO', 0),
                            'percent_to_decimal'
                        )
                        
                        processed_data[year] = {
                            'asset_liability_ratio': asset_liability_ratio,
                        }
            elif isinstance(balance_data, pd.DataFrame):
                # 模拟数据格式（行是指标，列是年份）
                for year in years:
                    if year in balance_data.columns:
                        processed_data[year] = {
                            'asset_liability_ratio': self.convert_unit(
                                balance_data.loc['负债合计', year] / balance_data.loc['资产总计', year] * 100,
                                'percent_to_decimal'
                            ),
                        }
            
            logger.info("资产负债表数据处理完成")
            return processed_data
            
        except Exception as e:
            logger.error(f"资产负债表数据处理失败: {e}")
            return processed_data
    
    def process_cash_flow_statement(self, cash_flow_data, years=None):
        """
        处理现金流量表数据
        :param cash_flow_data: 现金流量表原始数据
        :param years: 需要处理的年份列表
        :return: 处理后的现金流量表数据
        """
        if years is None:
            years = Constants.YEAR_RANGE
            
        processed_data = {}
        
        try:
            # 检查数据格式，处理模拟数据和爬虫数据的差异
            if isinstance(cash_flow_data, pd.DataFrame) and 'YEAR' in cash_flow_data.columns:
                # 爬虫获取的数据格式
                for year in years:
                    year_data = cash_flow_data[cash_flow_data['YEAR'] == year]
                    if not year_data.empty:
                        row = year_data.iloc[0]
                        
                        # 处理经营活动现金流量净额（如果有数据的话，万元转亿元）
                        operating_cash_flow = self.convert_unit(
                            row.get('OPERATING_CASH_FLOW', 0)
                        )
                        
                        processed_data[year] = {
                            'operating_cash_flow': operating_cash_flow,
                        }
            elif isinstance(cash_flow_data, pd.DataFrame):
                # 模拟数据格式（行是指标，列是年份）
                for year in years:
                    if year in cash_flow_data.columns:
                        processed_data[year] = {
                            'operating_cash_flow': self.convert_unit(cash_flow_data.loc['经营活动产生的现金流量净额', year]),
                        }
            
            logger.info("现金流量表数据处理完成")
            return processed_data
            
        except Exception as e:
            logger.error(f"现金流量表数据处理失败: {e}")
            return processed_data
    
    def process_company_info(self, company_info):
        """
        处理公司信息
        :param company_info: 公司信息原始数据
        :return: 处理后的公司信息
        """
        try:
            processed_info = {
                'stock_code': company_info.get('SECURITY_CODE', ''),
                'stock_name': company_info.get('SECURITY_NAME_ABBR', ''),
                'industry': company_info.get('PUBLISHNAME', ''),
            }
            
            logger.info("公司信息处理完成")
            return processed_info
            
        except Exception as e:
            logger.error(f"公司信息处理失败: {e}")
            return {}
    
    def process_valuation_data(self, valuation_data):
        """
        处理估值数据
        :param valuation_data: 估值原始数据
        :return: 处理后的估值数据
        """
        try:
            processed_valuation = {
                'pe': round(valuation_data.get('pe_ttm', 0), self.decimal_places),
                'pb': round(valuation_data.get('pb', 0), self.decimal_places),
                'eps': round(valuation_data.get('eps', 0), self.decimal_places),
            }
            
            logger.info("估值数据处理完成")
            return processed_valuation
            
        except Exception as e:
            logger.error(f"估值数据处理失败: {e}")
            return {}
    
    def process_financial_data(self, financial_data):
        """
        处理所有财务数据
        :param financial_data: 包含三大报表和其他数据的字典
        :return: 整合处理后的财务数据
        """
        processed_data = {
            'financial_indicators': {},
            'company_info': {},
            'valuation_indicators': {}
        }
        
        try:
            # 确保所有年份都有数据结构，防止年份错位
            for year in Constants.YEAR_RANGE:
                processed_data['financial_indicators'][year] = {}
            
            # 处理利润表
            if 'income_statement' in financial_data:
                income_processed = self.process_income_statement(financial_data['income_statement'])
                
                # 整合收入和净利润数据
                for year in income_processed:
                    if year in Constants.YEAR_RANGE:
                        processed_data['financial_indicators'][year]['revenue'] = income_processed[year]['revenue']
                        processed_data['financial_indicators'][year]['net_profit'] = income_processed[year]['net_profit']
                        
                        if 'revenue_growth_rate' in income_processed[year]:
                            processed_data['financial_indicators'][year]['revenue_growth_rate'] = income_processed[year]['revenue_growth_rate']
                        
                        if 'net_profit_growth_rate' in income_processed[year]:
                            processed_data['financial_indicators'][year]['net_profit_growth_rate'] = income_processed[year]['net_profit_growth_rate']
            
            # 处理资产负债表
            if 'balance_sheet' in financial_data:
                balance_processed = self.process_balance_sheet(financial_data['balance_sheet'])
                
                for year in balance_processed:
                    if year in Constants.YEAR_RANGE:
                        if 'asset_liability_ratio' in balance_processed[year]:
                            processed_data['financial_indicators'][year]['asset_liability_ratio'] = balance_processed[year]['asset_liability_ratio']
            
            # 处理现金流量表
            if 'cash_flow_statement' in financial_data:
                cash_processed = self.process_cash_flow_statement(financial_data['cash_flow_statement'])
                
                for year in cash_processed:
                    if year in Constants.YEAR_RANGE:
                        if 'operating_cash_flow' in cash_processed[year]:
                            processed_data['financial_indicators'][year]['operating_cash_flow'] = cash_processed[year]['operating_cash_flow']
            
            # 处理ROE
            if 'income_statement' in financial_data:
                income_data = financial_data['income_statement']
                # 检查数据格式，处理模拟数据和爬虫数据的差异
                if isinstance(income_data, pd.DataFrame) and 'YEAR' in income_data.columns:
                    # 爬虫数据格式
                    for year in Constants.YEAR_RANGE:
                        year_data = income_data[income_data['YEAR'] == year]
                        if not year_data.empty:
                            row = year_data.iloc[0]
                            roe = round(float(row.get('WEIGHTAVG_ROE', 0)), self.decimal_places)
                            processed_data['financial_indicators'][year]['roe'] = roe
                        else:
                            # 确保即使没有数据也有默认值
                            processed_data['financial_indicators'][year]['roe'] = 0.0
                elif isinstance(income_data, pd.DataFrame):
                    # 模拟数据格式
                    try:
                        # 先检查'净资产收益率'是否在索引中
                        if '净资产收益率' in income_data.index:
                            # 获取净资产收益率的所有行（可能有重复索引）
                            roe_rows = income_data.loc[['净资产收益率']]
                            
                            # 只取第一个净资产收益率行
                            if isinstance(roe_rows, pd.DataFrame):
                                roe_row = roe_rows.iloc[0]
                            else:
                                roe_row = roe_rows
                            
                            for year in Constants.YEAR_RANGE:
                                try:
                                    # 安全地检查年份是否在列中
                                    if year in income_data.columns.tolist():
                                        # 从行中获取标量值
                                        roe_value = roe_row[year]
                                        
                                        # 检查是否为数值类型
                                        if isinstance(roe_value, (int, float)):
                                            roe = round(roe_value, self.decimal_places)
                                        else:
                                            # 尝试转换为数值
                                            roe = round(float(roe_value) if pd.notna(roe_value) else 0, self.decimal_places)
                                        processed_data['financial_indicators'][year]['roe'] = roe
                                    else:
                                        # 确保即使没有数据也有默认值
                                        processed_data['financial_indicators'][year]['roe'] = 0.0
                                except Exception as e:
                                    logger.warning(f"处理ROE数据时出错 (年份: {year}): {e}")
                                    processed_data['financial_indicators'][year]['roe'] = 0.0
                    except Exception as e:
                        logger.error(f"处理ROE数据时发生严重错误: {e}")
                        # 为所有年份设置默认ROE值
                        for year in Constants.YEAR_RANGE:
                            processed_data['financial_indicators'][year]['roe'] = 0.0
            
            # 处理公司信息
            if 'company_info' in financial_data:
                processed_data['company_info'] = self.process_company_info(financial_data['company_info'])
            
            # 处理估值数据
            if 'valuation_data' in financial_data:
                processed_data['valuation_indicators'] = self.process_valuation_data(financial_data['valuation_data'])
            
            logger.info("所有财务数据处理完成")
            return processed_data
            
        except Exception as e:
            logger.error(f"财务数据处理失败: {e}")
            return processed_data
    
    def audit_financial_data(self, financial_data):
        """
        审计校验财务数据
        :param financial_data: 处理后的财务数据
        :return: 审计结果
        """
        audit_result = {
            'passed': True,
            'issues': []
        }
        
        try:
            # 检查数据完整性
            missing_years = []
            for year in Constants.YEAR_RANGE:
                if year not in financial_data['financial_indicators']:
                    missing_years.append(year)
            
            if missing_years:
                audit_result['passed'] = False
                audit_result['issues'].append(f"缺少年份数据: {missing_years}")
            
            # 检查核心指标完整性
            for year in Constants.YEAR_RANGE:
                if year in financial_data['financial_indicators']:
                    indicators = financial_data['financial_indicators'][year]
                    missing_indicators = []
                    
                    # 检查核心指标
                    core_indicators = ['revenue', 'net_profit', 'roe']
                    for indicator in core_indicators:
                        if indicator not in indicators or indicators[indicator] in self.error_values.values():
                            missing_indicators.append(indicator)
                    
                    if missing_indicators:
                        audit_result['passed'] = False
                        audit_result['issues'].append(f"{year}年缺少核心指标: {missing_indicators}")
            
            logger.info(f"财务数据审计完成，结果: {'通过' if audit_result['passed'] else '未通过'}")
            if not audit_result['passed']:
                logger.warning(f"审计问题: {audit_result['issues']}")
                
            return audit_result
            
        except Exception as e:
            logger.error(f"财务数据审计失败: {e}")
            audit_result['passed'] = False
            audit_result['issues'].append(f"审计过程出错: {str(e)}")
            return audit_result
    
    def calculate_extended_metrics(self, financial_data):
        """
        计算跨表扩展指标
        :param financial_data: 包含三大报表的财务数据
        :return: 包含扩展指标的字典
        """
        extended_metrics = {}
        
        try:
            # 确保所有年份都有数据结构
            for year in Constants.YEAR_RANGE:
                extended_metrics[year] = {}
            
            # 优先从主要财务指标接口获取数据
            key_indicators = financial_data.get('key_indicators', pd.DataFrame())
            
            # 处理主要财务指标数据
            if isinstance(key_indicators, pd.DataFrame) and not key_indicators.empty:
                for year in Constants.YEAR_RANGE:
                    year_data = key_indicators[key_indicators['YEAR'] == year]
                    if not year_data.empty:
                        row = year_data.iloc[0]
                        
                        # 毛利率
                        if 'GROSS_MARGIN' in row:
                            gross_margin = row.get('GROSS_MARGIN', 0)
                            extended_metrics[year]['gross_margin'] = self.clean_value(
                                gross_margin, 
                                FieldMapping.INDICATOR_MAP.get('gross_margin', {'decimal_places': 2})
                            )
                        
                        # 净利率
                        if 'NET_MARGIN' in row:
                            net_margin = row.get('NET_MARGIN', 0)
                            extended_metrics[year]['net_margin'] = self.clean_value(
                                net_margin, 
                                FieldMapping.INDICATOR_MAP.get('net_margin', {'decimal_places': 2})
                            )
                        
                        # 资产负债率
                        if 'DEBT_ASSET_RATIO' in row:
                            debt_ratio = row.get('DEBT_ASSET_RATIO', 0)
                            extended_metrics[year]['debt_asset_ratio'] = self.clean_value(
                                debt_ratio, 
                                FieldMapping.INDICATOR_MAP.get('debt_asset_ratio', {'decimal_places': 2})
                            )
                        
                        # 每股经营现金流
                        if 'OCFPS' in row:
                            ocfps = row.get('OCFPS', 0)
                            extended_metrics[year]['ocfps'] = self.clean_value(
                                ocfps, 
                                FieldMapping.INDICATOR_MAP.get('ocfps', {'decimal_places': 2})
                            )
                        
                        # 每股净资产
                        if 'BPS' in row:
                            bps = row.get('BPS', 0)
                            extended_metrics[year]['bps'] = self.clean_value(
                                bps, 
                                FieldMapping.INDICATOR_MAP.get('bps', {'decimal_places': 2})
                            )
                        
                        # 每股收益
                        if 'EPS' in row:
                            eps = row.get('EPS', 0)
                            extended_metrics[year]['eps'] = self.clean_value(
                                eps, 
                                FieldMapping.INDICATOR_MAP.get('eps', {'decimal_places': 2})
                            )
                        

            
            # 手动计算所有指标，确保即使主要财务指标接口调用失败，手动计算也能正确执行
            # 计算毛利率和净利率
            if 'income_statement' in financial_data:
                income_data = financial_data['income_statement']
                if isinstance(income_data, pd.DataFrame):
                    # 输出利润表的结构和字段名
                    logger.info(f"利润表字段名: {list(income_data.columns)}")
                    logger.info(f"利润表数据类型: {type(income_data)}")
                    logger.info(f"利润表是否为空: {income_data.empty}")
                    
                    if 'YEAR' in income_data.columns:
                        for year in Constants.YEAR_RANGE:
                            year_data = income_data[income_data['YEAR'] == year]
                            logger.info(f"2020年利润表数据: {not year_data.empty}")
                            if not year_data.empty:
                                row = year_data.iloc[0]
                                logger.info(f"利润表行数据: {row.to_dict()}")
                                
                                # 计算毛利率
                                total_revenue = row.get('TOTAL_OPERATE_INCOME', 0)
                                operating_cost = row.get('TOTAL_OPERATE_COST', 0)
                                
                                # 尝试从其他字段获取毛利率信息
                                gross_margin = 0
                                if 'XSMLL' in row:  # 销售毛利率
                                    gross_margin = row.get('XSMLL', 0)
                                elif total_revenue > 0 and operating_cost > 0:
                                    gross_margin = ((total_revenue - operating_cost) / total_revenue) * 100
                                elif total_revenue > 0:
                                    # 如果没有营业成本数据，设置为0.0
                                    gross_margin = 0.0
                                
                                logger.info(f"营业收入: {total_revenue}, 营业成本: {operating_cost}, 毛利率: {gross_margin}")
                                extended_metrics[year]['gross_margin'] = self.clean_value(
                                    gross_margin, 
                                    FieldMapping.INDICATOR_MAP.get('gross_margin', {'decimal_places': 2})
                                )
                                
                                # 计算净利率（净利润/营业收入）
                                total_revenue = row.get('TOTAL_OPERATE_INCOME', 0)
                                net_profit = row.get('PARENT_NETPROFIT', 0)
                                logger.info(f"净利润: {net_profit}")
                                if total_revenue > 0:
                                    net_margin = (net_profit / total_revenue) * 100
                                    logger.info(f"净利率: {net_margin}")
                                    extended_metrics[year]['net_margin'] = self.clean_value(
                                        net_margin, 
                                        FieldMapping.INDICATOR_MAP.get('net_margin', {'decimal_places': 2})
                                    )
            
            # 计算净利润含金量（经营现金流/净利润）
            if 'cash_flow_statement' in financial_data and 'income_statement' in financial_data:
                cash_data = financial_data['cash_flow_statement']
                income_data = financial_data['income_statement']
                
                if isinstance(cash_data, pd.DataFrame):
                    logger.info(f"现金流量表字段名: {list(cash_data.columns)}")
                    logger.info(f"现金流量表数据类型: {type(cash_data)}")
                    logger.info(f"现金流量表是否为空: {cash_data.empty}")
                
                if (isinstance(cash_data, pd.DataFrame) and 'YEAR' in cash_data.columns and
                    isinstance(income_data, pd.DataFrame) and 'YEAR' in income_data.columns):
                    for year in Constants.YEAR_RANGE:
                        cash_year_data = cash_data[cash_data['YEAR'] == year]
                        income_year_data = income_data[income_data['YEAR'] == year]
                        
                        logger.info(f"2020年现金流量表数据: {not cash_year_data.empty}")
                        if not cash_year_data.empty and not income_year_data.empty:
                            cash_row = cash_year_data.iloc[0]
                            income_row = income_year_data.iloc[0]
                            logger.info(f"现金流量表行数据: {cash_row.to_dict()}")
                            
                            # 归母净利润
                            net_profit = income_row.get('PARENT_NETPROFIT', 0)
                            
                            # 经营活动产生的现金流量净额
                            operating_cash_flow = cash_row.get('OPERATING_CASH_FLOW', 0) or \
                                                 cash_row.get('N_CASH_FLOWS_FROM_OPERATING_A', 0) or \
                                                 cash_row.get('NETCASH_OPERATE', 0)
                            
                            # 尝试从其他字段获取经营活动现金流量信息
                            if operating_cash_flow == 0:
                                if 'MGJYXJJE' in income_row:  # 每股经营活动现金流量
                                    basic_eps = income_row.get('BASIC_EPS', 1)
                                    if basic_eps > 0 and net_profit > 0:
                                        # 估算经营活动现金流量：每股经营活动现金流量 * (净利润 / 每股收益)
                                        operating_cash_flow_per_share = income_row.get('MGJYXJJE', 0)
                                        estimated_shares = net_profit / basic_eps
                                        operating_cash_flow = operating_cash_flow_per_share * estimated_shares
                                elif net_profit > 0:
                                    # 如果没有现金流量数据，假设净利润含金量为100%
                                    operating_cash_flow = net_profit
                            logger.info(f"经营活动产生的现金流量净额: {operating_cash_flow}")
                            
                            if net_profit > 0:
                                cash_ratio = (operating_cash_flow / net_profit)
                                logger.info(f"净利润含金量: {cash_ratio * 100}%")
                                # 存储小数形式，让Excel的百分比格式处理显示
                                extended_metrics[year]['net_profit_cash_ratio'] = round(cash_ratio, 4)
            
            # 计算资产负债率（负债合计/资产合计）和ROE（净资产收益率）
            if 'balance_sheet' in financial_data and 'income_statement' in financial_data:
                balance_data = financial_data['balance_sheet']
                income_data = financial_data['income_statement']
                
                if isinstance(balance_data, pd.DataFrame):
                    logger.info(f"资产负债表字段名: {list(balance_data.columns)}")
                    logger.info(f"资产负债表数据类型: {type(balance_data)}")
                    logger.info(f"资产负债表是否为空: {balance_data.empty}")
                
                if isinstance(balance_data, pd.DataFrame) and 'YEAR' in balance_data.columns and isinstance(income_data, pd.DataFrame) and 'YEAR' in income_data.columns:
                    # 构建年份到股东权益的映射
                    equity_map = {}
                    for year in Constants.YEAR_RANGE:
                        year_data = balance_data[balance_data['YEAR'] == year]
                        if not year_data.empty:
                            row = year_data.iloc[0]
                            total_equity = row.get('TOTAL_EQUITY', 0)
                            equity_map[year] = total_equity
                            logger.info(f"{year}年股东权益: {total_equity}")
                    
                    # 计算ROE和资产负债率
                    for year in Constants.YEAR_RANGE:
                        year_data = balance_data[balance_data['YEAR'] == year]
                        income_year_data = income_data[income_data['YEAR'] == year]
                        logger.info(f"{year}年资产负债表数据: {not year_data.empty}, 利润表数据: {not income_year_data.empty}")
                        
                        if not year_data.empty:
                            row = year_data.iloc[0]
                            logger.info(f"资产负债表行数据: {row.to_dict()}")
                            
                            # 计算资产负债率
                            total_liabilities = row.get('TOTAL_LIABILITIES', 0)
                            total_assets = row.get('TOTAL_ASSETS', 0)
                            logger.info(f"负债合计: {total_liabilities}, 资产合计: {total_assets}")
                            
                            if total_assets > 0:
                                debt_ratio = (total_liabilities / total_assets) * 100
                                logger.info(f"资产负债率: {debt_ratio}")
                                extended_metrics[year]['debt_asset_ratio'] = self.clean_value(
                                    debt_ratio, 
                                    FieldMapping.INDICATOR_MAP.get('debt_asset_ratio', {'decimal_places': 2})
                                )
                        
                        # 计算ROE
                        if not year_data.empty and not income_year_data.empty:
                            balance_row = year_data.iloc[0]
                            income_row = income_year_data.iloc[0]
                            
                            # 获取当前年份的净利润
                            net_profit = income_row.get('PARENT_NETPROFIT', 0)
                            logger.info(f"{year}年净利润: {net_profit}")
                            
                            # 获取当前年份和上一年份的股东权益
                            current_equity = equity_map.get(year, 0)
                            previous_equity = equity_map.get(year - 1, 0)
                            
                            # 计算平均股东权益
                            if current_equity > 0 or previous_equity > 0:
                                avg_equity = (current_equity + previous_equity) / 2
                                logger.info(f"{year}年平均股东权益: {avg_equity}")
                                
                                # 计算ROE
                                if avg_equity > 0:
                                    roe = (net_profit / avg_equity) * 100
                                    logger.info(f"{year}年ROE: {roe}")
                                    extended_metrics[year]['roe'] = self.clean_value(
                                        roe, 
                                        FieldMapping.INDICATOR_MAP.get('roe', {'decimal_places': 2})
                                    )
            
            # 计算分红率（分配股利、利润或偿付利息支付的现金/净利润）
            if 'cash_flow_statement' in financial_data and 'income_statement' in financial_data:
                cash_data = financial_data['cash_flow_statement']
                income_data = financial_data['income_statement']
                
                if (isinstance(cash_data, pd.DataFrame) and 'YEAR' in cash_data.columns and
                    isinstance(income_data, pd.DataFrame) and 'YEAR' in income_data.columns):
                    for year in Constants.YEAR_RANGE:
                        cash_year_data = cash_data[cash_data['YEAR'] == year]
                        income_year_data = income_data[income_data['YEAR'] == year]
                        
                        if not cash_year_data.empty and not income_year_data.empty:
                            cash_row = cash_year_data.iloc[0]
                            income_row = income_year_data.iloc[0]
                            
                            # 分配股利、利润或偿付利息支付的现金
                            dividends_paid = cash_row.get('CASH_PAID_FOR_DIVIDENDS_PROFITS_INTEREST', 0) or \
                                           cash_row.get('CASH_PAID_FOR_DIVIDENDS_AND_INTEREST', 0) or \
                                           cash_row.get('N_CASH_FLOWS_FROM_FINANCING_A', 0)
                            
                            # 尝试从其他字段获取分红信息
                            if dividends_paid == 0:
                                # 尝试从利润表中获取分红信息
                                if 'BASIC_EPS' in income_row:  # 每股收益
                                    basic_eps = income_row.get('BASIC_EPS', 0)
                                    if basic_eps > 0:
                                        # 假设分红率为50%
                                        net_profit = income_row.get('PARENT_NETPROFIT', 0)
                                        if net_profit > 0:
                                            dividends_paid = net_profit * 0.5
                                            logger.info(f"基于每股收益计算分红金额: {dividends_paid}")
                            
                            # 归母净利润
                            net_profit = income_row.get('PARENT_NETPROFIT', 0)
                            

            
            # 计算每股经营现金流、每股净资产和每股收益
            if 'income_statement' in financial_data:
                income_data = financial_data['income_statement']
                
                if isinstance(income_data, pd.DataFrame) and 'YEAR' in income_data.columns:
                    for year in Constants.YEAR_RANGE:
                        income_year_data = income_data[income_data['YEAR'] == year]
                        
                        if not income_year_data.empty:
                            income_row = income_year_data.iloc[0]
                            
                            # 每股经营现金流
                            ocfps = income_row.get('MGJYXJJE', 0)  # 每股经营活动现金流量
                            
                            # 如果没有每股经营活动现金流量字段，基于净利润和总股本估算
                            if ocfps == 0:
                                net_profit = income_row.get('PARENT_NETPROFIT', 0)
                                # 从financial_data中获取总股本数据
                                total_shares = financial_data.get('share_capital', 0)
                                logger.info(f"使用总股本数据: {total_shares}股")
                                
                                # 如果没有获取到总股本数据，使用默认值
                                if total_shares <= 0:
                                    total_shares = 0.0
                                    logger.warning("未获取到总股本数据，使用默认值: 0.0股")
                                    ocfps = 'N/A'
                                else:
                                    # 假设净利润含金量为100%
                                    operating_cash_flow = net_profit
                                    ocfps = operating_cash_flow / total_shares
                                    logger.info(f"基于净利润估算每股经营现金流: {ocfps}")
                            
                            if ocfps != 'N/A':
                                extended_metrics[year]['ocfps'] = self.clean_value(
                                    ocfps, 
                                    FieldMapping.INDICATOR_MAP.get('ocfps', {'decimal_places': 2})
                                )
                            else:
                                extended_metrics[year]['ocfps'] = ocfps
                            
                            # 每股净资产
                            bps = income_row.get('BPS', 0)  # 每股净资产
                            
                            # 如果没有每股净资产字段，基于总股本估算
                            if bps == 0:
                                # 从financial_data中获取总股本数据
                                total_shares = financial_data.get('share_capital', 0)
                                logger.info(f"使用总股本数据: {total_shares}股")
                                
                                # 如果没有获取到总股本数据，使用默认值
                                if total_shares <= 0:
                                    total_shares = 0.0
                                    logger.warning("未获取到总股本数据，使用默认值: 0.0股")
                                if total_shares > 0:
                                    # 尝试从资产负债表获取总股本
                                    if 'balance_sheet' in financial_data:
                                        balance_data = financial_data['balance_sheet']
                                        if isinstance(balance_data, pd.DataFrame) and 'YEAR' in balance_data.columns:
                                            balance_year_data = balance_data[balance_data['YEAR'] == year]
                                            if not balance_year_data.empty:
                                                balance_row = balance_year_data.iloc[0]
                                                total_equity = balance_row.get('TOTAL_EQUITY', 0)
                                                if total_equity > 0:
                                                    bps = total_equity / total_shares
                                                    logger.info(f"基于资产负债表估算每股净资产: {bps}")
                            
                            extended_metrics[year]['bps'] = self.clean_value(
                                bps, 
                                FieldMapping.INDICATOR_MAP.get('bps', {'decimal_places': 2})
                            )
                            
                            # 每股收益
                            basic_eps = income_row.get('BASIC_EPS', 0)  # 每股收益
                            extended_metrics[year]['eps'] = self.clean_value(
                                basic_eps, 
                                FieldMapping.INDICATOR_MAP.get('eps', {'decimal_places': 2})
                            )
            
            # 尝试从资产负债表获取每股净资产
            if 'balance_sheet' in financial_data:
                balance_data = financial_data['balance_sheet']
                
                if isinstance(balance_data, pd.DataFrame) and 'YEAR' in balance_data.columns:
                    for year in Constants.YEAR_RANGE:
                        balance_year_data = balance_data[balance_data['YEAR'] == year]
                        
                        if not balance_year_data.empty:
                            balance_row = balance_year_data.iloc[0]
                            
                            # 从financial_data中获取总股本数据
                            total_shares = financial_data.get('share_capital', 0)
                            logger.info(f"使用总股本数据: {total_shares}股")
                            
                            # 如果没有获取到总股本数据，使用默认值
                            if total_shares <= 0:
                                total_shares = 0.0
                                logger.warning("未获取到总股本数据，使用默认值: 0.0股")
                                # 当总股本为0时，相关指标显示为N/A
                                extended_metrics[year]['bps'] = 'N/A'
                                extended_metrics[year]['ocfps'] = 'N/A'
                                extended_metrics[year]['eps'] = 'N/A'
                                continue
                            
                            # 每股净资产
                            total_equity = balance_row.get('TOTAL_EQUITY', 0)
                            bps = total_equity / total_shares
                            extended_metrics[year]['bps'] = self.clean_value(
                                bps, 
                                FieldMapping.INDICATOR_MAP.get('bps', {'decimal_places': 2})
                            )
            
            # 计算股息率（每股分红 / 当前股价 * 100%）
            if 'income_statement' in financial_data and 'valuation_data' in financial_data:
                income_data = financial_data['income_statement']
                valuation_data = financial_data['valuation_data']
                if isinstance(income_data, pd.DataFrame) and 'YEAR' in income_data.columns:
                    for year in Constants.YEAR_RANGE:
                        income_year_data = income_data[income_data['YEAR'] == year]
                        if not income_year_data.empty:
                            income_row = income_year_data.iloc[0]
                            
                            # 尝试从利润表中获取分红信息
                            dividend_per_share = 0
                            if 'ASSIGNDSCRPT' in income_row:  # 分配方案
                                assign_desc = income_row.get('ASSIGNDSCRPT', '')
                                logger.info(f"分配方案: {assign_desc}")
                                # 为了简化，我们假设每股分红为1元
                                dividend_per_share = 1.0
                            elif 'BASIC_EPS' in income_row:  # 每股收益
                                basic_eps = income_row.get('BASIC_EPS', 0)
                                if basic_eps > 0:
                                    # 假设分红率为50%
                                    dividend_per_share = basic_eps * 0.5
                            
                            # 获取当前股价
                            current_price = valuation_data.get('current_price', 0)
                            logger.info(f"每股分红: {dividend_per_share}, 当前股价: {current_price}")

            # 健壮性处理：确保所有年份都有所有指标的默认值
            for year in Constants.YEAR_RANGE:
                # 确保毛利率存在
                if 'gross_margin' not in extended_metrics[year]:
                    extended_metrics[year]['gross_margin'] = 0.0
                
                # 确保净利率存在
                if 'net_margin' not in extended_metrics[year]:
                    extended_metrics[year]['net_margin'] = 0.0
                
                # 确保净利润含金量存在
                if 'net_profit_cash_ratio' not in extended_metrics[year]:
                    extended_metrics[year]['net_profit_cash_ratio'] = 0.0
                
                # 确保资产负债率存在
                if 'debt_asset_ratio' not in extended_metrics[year]:
                    extended_metrics[year]['debt_asset_ratio'] = 0.0
                

                

                
                # 确保每股经营现金流存在
                if 'ocfps' not in extended_metrics[year]:
                    extended_metrics[year]['ocfps'] = 0.0
                
                # 确保每股净资产存在
                if 'bps' not in extended_metrics[year]:
                    extended_metrics[year]['bps'] = 0.0
                
                # 确保每股收益存在
                if 'eps' not in extended_metrics[year]:
                    extended_metrics[year]['eps'] = 0.0
            
            logger.info("扩展指标计算完成")
            return extended_metrics
            
        except Exception as e:
            logger.error(f"扩展指标计算失败: {e}")
            # 确保即使出错也返回所有年份的默认值
            for year in Constants.YEAR_RANGE:
                if year not in extended_metrics:
                    extended_metrics[year] = {}
                
                # 确保所有指标都有默认值
                default_metrics = {
                    'gross_margin': 0.0,
                    'net_margin': 0.0,
                    'net_profit_cash_ratio': 0.0,
                    'debt_asset_ratio': 0.0,
                    'ocfps': 0.0,
                    'bps': 0.0,
                    'eps': 0.0
                }
                
                for metric, value in default_metrics.items():
                    if metric not in extended_metrics[year]:
                        extended_metrics[year][metric] = value
            
            return extended_metrics
    
    def process_financial_data_for_multicolumn(self, financial_data):
        """
        处理财务数据，转换为适合多列填充的格式
        :param financial_data: 原始财务数据
        :return: 按年份组织的财务数据字典
        """
        processed_data = {}
        
        try:
            # 确保所有年份都有数据结构
            for year in Constants.YEAR_RANGE:
                processed_data[year] = {}
            
            # 处理利润表数据
            if 'income_statement' in financial_data:
                income_data = financial_data['income_statement']
                if isinstance(income_data, pd.DataFrame) and 'YEAR' in income_data.columns:
                    for year in Constants.YEAR_RANGE:
                        year_data = income_data[income_data['YEAR'] == year]
                        if not year_data.empty:
                            row = year_data.iloc[0]
                            
                            # 营业总收入（元转亿元）
                            total_revenue = row.get('TOTAL_OPERATE_INCOME', 0)
                            processed_data[year]['total_revenue'] = self.clean_value(
                                total_revenue, 
                                FieldMapping.INDICATOR_MAP['total_revenue']
                            )
                            
                            # 归母净利润（元转亿元）
                            net_profit = row.get('PARENT_NETPROFIT', 0)
                            processed_data[year]['net_profit'] = self.clean_value(
                                net_profit, 
                                FieldMapping.INDICATOR_MAP['net_profit']
                            )
                            
                            # ROE
                            roe = row.get('WEIGHTAVG_ROE', 0)
                            processed_data[year]['roe'] = self.clean_value(
                                roe, 
                                FieldMapping.INDICATOR_MAP['roe']
                            )
            
            # 处理现金流量表数据
            if 'cash_flow_statement' in financial_data:
                cash_data = financial_data['cash_flow_statement']
                if isinstance(cash_data, pd.DataFrame) and 'YEAR' in cash_data.columns:
                    for year in Constants.YEAR_RANGE:
                        year_data = cash_data[cash_data['YEAR'] == year]
                        if not year_data.empty:
                            row = year_data.iloc[0]
                            
                            # 经营性现金流（元转亿元）
                            operating_cash_flow = row.get('OPERATING_CASH_FLOW', 0) or \
                                                 row.get('N_CASH_FLOWS_FROM_OPERATING_A', 0)
                            processed_data[year]['operating_cash_flow'] = self.clean_value(
                                operating_cash_flow, 
                                FieldMapping.INDICATOR_MAP.get('operating_cash_flow', {'decimal_places': 2})
                            )
            
            # 计算增长率
            sorted_years = sorted(Constants.YEAR_RANGE)
            for i in range(1, len(sorted_years)):
                current_year = sorted_years[i]
                previous_year = sorted_years[i-1]
                
                if current_year in processed_data and previous_year in processed_data:
                    # 营业收入增长率
                    if 'total_revenue' in processed_data[current_year] and 'total_revenue' in processed_data[previous_year]:
                        current_revenue = processed_data[current_year]['total_revenue'] * 1e8  # 转回元计算
                        previous_revenue = processed_data[previous_year]['total_revenue'] * 1e8
                        revenue_growth = self.calculate_growth_rate(current_revenue, previous_revenue, is_percentage=True)
                        processed_data[current_year]['revenue_growth'] = self.clean_value(
                            revenue_growth, 
                            FieldMapping.INDICATOR_MAP['revenue_growth']
                        )
                    
                    # 净利润增长率
                    if 'net_profit' in processed_data[current_year] and 'net_profit' in processed_data[previous_year]:
                        current_profit = processed_data[current_year]['net_profit'] * 1e8  # 转回元计算
                        previous_profit = processed_data[previous_year]['net_profit'] * 1e8
                        profit_growth = self.calculate_growth_rate(current_profit, previous_profit, is_percentage=True)
                        processed_data[current_year]['profit_growth'] = self.clean_value(
                            profit_growth, 
                            FieldMapping.INDICATOR_MAP['profit_growth']
                        )
            
            # 计算扩展指标
            extended_metrics = self.calculate_extended_metrics(financial_data)
            
            # 合并扩展指标
            for year in extended_metrics:
                for metric, value in extended_metrics[year].items():
                    processed_data[year][metric] = value
            
            # 处理公司信息
            if 'company_info' in financial_data:
                company_info = financial_data['company_info']
                
                # 解析公司信息（现在scraper返回的是从财务报表中提取的字典）
                stock_name = ''
                industry = ''
                
                if isinstance(company_info, dict):
                    stock_name = company_info.get('SECURITY_NAME_ABBR', '')
                    industry = company_info.get('INDUSTRY', '')
                    logger.info(f"从company_info字典提取: stock_name={stock_name}, industry={industry}")
                elif isinstance(company_info, list) and len(company_info) > 0:
                    first_item = company_info[0]
                    if isinstance(first_item, dict):
                        stock_name = first_item.get('SECURITY_NAME_ABBR', '')
                        industry = first_item.get('INDUSTRY', '')
                        logger.info(f"从company_info列表提取: stock_name={stock_name}, industry={industry}")
                
                # 处理估值数据（scraper已经完成单位转换和PE/PB计算）
                current_price = 0
                total_market_cap = 0
                pe_ratio = 0
                pb_ratio = 0
                
                if 'valuation_data' in financial_data:
                    valuation = financial_data['valuation_data']
                    current_price = valuation.get('current_price', 0) or 0
                    total_market_cap = valuation.get('total_market_cap', 0) or 0
                    pe_ratio = valuation.get('pe_ttm', 0) or 0
                    pb_ratio = valuation.get('pb', 0) or 0
                
                # 计算5年净利润复合增长率 (CAGR)
                cagr_5y = 'N/A'
                try:
                    if 2024 in processed_data and 2020 in processed_data:
                        profit_2024 = processed_data[2024].get('net_profit', 0) * 1e8  # 转回元
                        profit_2020 = processed_data[2020].get('net_profit', 0) * 1e8
                        
                        if profit_2020 > 0 and profit_2024 > 0:
                            import math
                            cagr_5y = math.pow((profit_2024 / profit_2020), 1/4) - 1
                            logger.info(f"CAGR计算: 2020年净利润={profit_2020}, 2024年净利润={profit_2024}, CAGR={cagr_5y}")
                        else:
                            logger.warning("CAGR计算: 2020或2024年净利润为负数或零，无法计算CAGR")
                except Exception as e:
                    logger.error(f"CAGR计算失败: {e}")
                
                processed_data['company_info'] = {
                    'stock_name': stock_name,
                    'current_price': current_price,
                    'total_market_cap': total_market_cap,
                    'industry': industry,
                    'pe_ratio': pe_ratio,
                    'pb_ratio': pb_ratio,
                    'cagr_5y': cagr_5y
                }
            
            logger.info("多列格式财务数据处理完成")
            return processed_data
            
        except Exception as e:
            logger.error(f"多列格式财务数据处理失败: {e}")
            return processed_data

if __name__ == "__main__":
    # 测试数据处理功能
    processor = DataProcessor()
    
    # 测试单位转换
    test_value = 12345678.90
    converted = processor.convert_unit(test_value, "ten_thousand_to_hundred_million")
    print(f"单位转换测试 - 原始值: {test_value}, 转换后: {converted}")
    
    # 测试增长率计算
    current = 1500
    previous = 1000
    growth_rate = processor.calculate_growth_rate(current, previous)
    print(f"增长率计算测试 - 当前值: {current}, 前一年值: {previous}, 增长率: {growth_rate}%")
    
    # 测试除零处理
    zero_growth = processor.calculate_growth_rate(1500, 0)
    print(f"除零处理测试 - 结果: {zero_growth}")


class InvestmentCalculator:
    """
    投资收益复利计算器
    
    计算逻辑（与Excel模板完全一致）：
    - 初始买入：2019年12月31日收盘价买入100股
    - 每年计算：
      - 分红可买入股数 = 前一年总股数 × 每股现金红利 ÷ 除权日收盘价
      - 送转股数 = 前一年总股数 × 每股送和转股数
      - 总股数 = 前一年总股数 + 分红可买入股数 + 送转股数
      - 市值 = 总股数 × 除权日收盘价
      - 投资收益率 = (市值 - 期初投资市值) ÷ 期初投资市值
    """
    
    def __init__(self):
        self.initial_shares = 100  # 初始持股数
        self.initial_year = 2019  # 初始年份
    
    def calculate_investment_return(self, dividend_data, initial_price, current_price, roe_data=None):
        """
        计算投资收益复利
        
        Args:
            dividend_data: 分红数据列表，每个元素包含：
                {
                    'year': 年份,
                    'ex_dividend_date': 除权除息日,
                    'cash_dividend_per_share': 每股现金红利,
                    'bonus_shares_per_share': 每股送转股数,
                    'ex_date_price': 除权日股价
                }
            initial_price: 初始买入价格（2019年底收盘价）
            current_price: 当前市场价
            roe_data: ROE数据字典 {年份: ROE值}
            
        Returns:
            计算结果字典，包含：
            {
                'years': 年份列表,
                'ex_dates': 除权日期列表,
                'dividends': 每股分红列表,
                'bonus_shares': 送转股数列表,
                'ex_prices': 除权日股价列表,
                'reinvest_shares': 分红再买入股数列表,
                'cumulative_shares': 累计持股数列表,
                'holdings_value': 持仓价值列表,
                'cumulative_return': 累计收益率列表,
                'roe_values': ROE值列表
            }
        """
        try:
            logger.info(f"[Investment Calculator] 开始计算投资收益...")
            logger.info(f"[Investment Calculator] 初始价格: {initial_price}, 当前价格: {current_price}")
            
            # 初始化结果字典
            result = {
                'years': [],
                'ex_dates': [],
                'dividends': [],
                'bonus_shares': [],
                'ex_prices': [],
                'reinvest_shares': [],
                'cumulative_shares': [],
                'holdings_value': [],
                'cumulative_return': [],
                'roe_values': []
            }
            
            # 初始持股数
            cumulative_shares = self.initial_shares
            
            # 初始投入成本
            if initial_price > 0:
                initial_cost = self.initial_shares * initial_price
                logger.info(f"[Investment Calculator] 初始持股: {cumulative_shares}, 初始成本: {initial_cost}")
            else:
                # 如果没有初始价格，从第一次分红开始计算
                initial_cost = 0
                logger.info(f"[Investment Calculator] 未获取到初始价格，将从第一次分红开始计算")
            
            # 按年份排序分红数据
            sorted_dividends = sorted(dividend_data, key=lambda x: x['year'])
            
            # 如果没有初始价格，从第一次分红开始计算
            if initial_price <= 0 and sorted_dividends:
                first_dividend = sorted_dividends[0]
                initial_price = first_dividend['ex_date_price']
                initial_cost = self.initial_shares * initial_price
                logger.info(f"[Investment Calculator] 使用第一次分红作为初始价格: {initial_price}, 初始成本: {initial_cost}")
            
            # 计算每年的数据
            for i, dividend_info in enumerate(sorted_dividends):
                year = dividend_info['year']
                ex_date = dividend_info['ex_dividend_date']
                cash_dividend = dividend_info['cash_dividend_per_share']
                bonus_shares = dividend_info['bonus_shares_per_share']
                ex_price = dividend_info['ex_date_price']
                
                # 使用除权日所在的年份作为显示年份
                display_year = ex_date.year if ex_date else year
                
                logger.info(f"[Investment Calculator] {display_year}年: 除权日={ex_date}, 分红={cash_dividend}, 送转={bonus_shares}, 除权价={ex_price}")
                
                # 计算分红再买入股数（Row 16）
                # 公式: (上一年度累计持股数 * 当年每股现金红利) / 当年除权日收盘价
                reinvest_shares = 0
                if cumulative_shares > 0 and cash_dividend > 0 and ex_price > 0:
                    reinvest_shares = (cumulative_shares * cash_dividend) / ex_price
                    reinvest_shares = round(reinvest_shares, 4)  # 保留4位小数
                    logger.info(f"[Investment Calculator] 分红再买入股数: {reinvest_shares}")
                
                # 计算送转增加股数（Row 17）
                # 公式: 上一年度累计持股数 * 当年每股送转股数
                bonus_increase_shares = 0
                if cumulative_shares > 0 and bonus_shares > 0:
                    bonus_increase_shares = cumulative_shares * bonus_shares
                    bonus_increase_shares = round(bonus_increase_shares, 4)  # 保留4位小数
                    logger.info(f"[Investment Calculator] 送转增加股数: {bonus_increase_shares}")
                
                # 计算本年度累计持股数（Row 18）
                # 公式: 上一年度累计持股数 + 当年分红再买入股数 + 当年送转增加股数
                cumulative_shares = cumulative_shares + reinvest_shares + bonus_increase_shares
                cumulative_shares = round(cumulative_shares, 4)  # 保留4位小数
                logger.info(f"[Investment Calculator] 本年度累计持股数: {cumulative_shares}")
                
                # 获取ROE值（使用分红年度）
                roe_value = roe_data.get(year, None) if roe_data else None
                
                # 添加到结果（使用除权日年份）
                result['years'].append(display_year)
                result['ex_dates'].append(ex_date if ex_date else '')
                result['dividends'].append(round(cash_dividend, 2) if cash_dividend > 0 else 0)
                result['bonus_shares'].append(round(bonus_shares, 4) if bonus_shares > 0 else 0)
                result['ex_prices'].append(round(ex_price, 2) if ex_price > 0 else 0)
                result['reinvest_shares'].append(reinvest_shares)
                result['cumulative_shares'].append(cumulative_shares)
                result['roe_values'].append(roe_value if roe_value else '')
            
            # 计算持仓价值和累计收益率
            for i, year in enumerate(result['years']):
                shares = result['cumulative_shares'][i]
                
                # 持仓价值 = 当前持股数 * 当前市场价
                holdings_value = shares * current_price
                result['holdings_value'].append(round(holdings_value, 2))
                
                # 累计收益率 = (持仓价值 - 初始投入成本) / 初始投入成本
                if initial_cost > 0:
                    cumulative_return = (holdings_value - initial_cost) / initial_cost
                    cumulative_return = round(cumulative_return, 4)
                else:
                    cumulative_return = 0
                
                result['cumulative_return'].append(cumulative_return)
            
            logger.info(f"[Investment Calculator] 计算完成")
            logger.info(f"[Investment Calculator] 最终持股数: {result['cumulative_shares'][-1] if result['cumulative_shares'] else 0}")
            logger.info(f"[Investment Calculator] 最终持仓价值: {result['holdings_value'][-1] if result['holdings_value'] else 0}")
            logger.info(f"[Investment Calculator] 最终累计收益率: {result['cumulative_return'][-1] if result['cumulative_return'] else 0}")
            
            return result
            
        except Exception as e:
            logger.exception(f"[Investment Calculator] 计算失败: {e}")
            return {
                'years': [],
                'ex_dates': [],
                'dividends': [],
                'bonus_shares': [],
                'ex_prices': [],
                'reinvest_shares': [],
                'cumulative_shares': [],
                'holdings_value': [],
                'cumulative_return': [],
                'roe_values': []
            }
