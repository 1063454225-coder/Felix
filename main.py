# -*- coding: utf-8 -*-
"""
主程序：实现命令行交互，整合数据抓取、处理和Excel写入功能
"""

import argparse
import logging
import os
from scraper import FinancialDataSpider
from processor import DataProcessor, InvestmentCalculator
from excel_handler import ExcelHandler
from config import Constants, LogConfig

# 配置日志
logging.basicConfig(
    level=getattr(logging, LogConfig.LOG_LEVEL),
    format=LogConfig.LOG_FORMAT,
    filename=LogConfig.LOG_FILE
)
logger = logging.getLogger(__name__)

class FinancialReportGenerator:
    def __init__(self):
        self.spider = FinancialDataSpider()
        self.processor = DataProcessor()
        self.investment_calculator = InvestmentCalculator()
        self.excel_handler = None
        
    def generate_report(self, stock_code, output_file):
        """
        生成财务报告
        :param stock_code: 股票代码
        :param output_file: 输出文件路径
        :return: 生成结果
        """
        try:
            logger.info(f"开始生成 {stock_code} 的财务报告...")
            
            # 1. 获取财务数据
            logger.info(f"正在抓取 {stock_code} 的财务数据...")
            financial_data = self.spider.get_company_financial_data(stock_code)
            logger.info(f"成功获取 {stock_code} 的财务数据")
            
            # 2. 处理财务数据（使用多列格式）
            logger.info("正在处理财务数据（多列格式）...")
            processed_data = self.processor.process_financial_data_for_multicolumn(financial_data)
            
            # 2.5 数据验证：打印核心指标到控制台
            logger.info("正在进行数据验证...")
            self._validate_multicolumn_data(processed_data, stock_code)
            
            # 3. 写入Excel（创建新文件）
            logger.info(f"正在创建Excel文件（多列格式）...")
            self.excel_handler = ExcelHandler()
            
            if not self.excel_handler.create_new_workbook():
                logger.error("创建Excel工作簿失败")
                return False
            
            if not self.excel_handler.write_multicolumn_data(processed_data, stock_code):
                logger.error("写入数据失败")
                return False
            
            # 3.5 计算并写入投资收益数据
            logger.info("正在计算投资收益...")
            investment_data = self._calculate_investment_return(stock_code, processed_data)
            
            # 即使没有初始价格，只要有分红数据就写入投资收益区域
            if investment_data and investment_data.get('years'):
                logger.info("正在写入投资收益区域...")
                self.excel_handler.setup_investment_return_structure()
                self.excel_handler.write_investment_return_data(investment_data)
            else:
                logger.warning("没有投资收益数据可写入")
            
            # 4. 保存Excel文件
            logger.info(f"正在保存Excel文件...")
            if not self.excel_handler.save_file(output_file):
                logger.error("保存Excel文件失败")
                return False
            
            # 5. 关闭Excel文件
            self.excel_handler.close()
            
            logger.info(f"财务报告生成成功: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"财务报告生成失败: {e}")
            return False
    
    def _validate_multicolumn_data(self, processed_data, stock_code):
        """
        数据验证：打印多列格式的核心指标到控制台
        :param processed_data: 处理后的数据（多列格式）
        :param stock_code: 股票代码
        """
        print("\n" + "="*80)
        print(f"数据验证（多列格式） - {stock_code}")
        print("="*80)
        
        # 打印公司信息
        if 'company_info' in processed_data:
            print("\n【公司信息】")
            for key, value in processed_data['company_info'].items():
                print(f"  {key}: {value}")
        
        # 打印财务指标
        print("\n【财务指标】")
        years = sorted([year for year in processed_data.keys() if isinstance(year, int)])
        
        # 打印表头
        print(f"{'年份':<8}", end="")
        indicators = ['total_revenue', 'net_profit', 'roe', 'revenue_growth', 'profit_growth', 
                      'gross_margin', 'net_margin', 'net_profit_cash_ratio', 'debt_asset_ratio', 
                      'ocfps', 'bps', 'eps']
        for indicator in indicators:
            print(f"{indicator:<25}", end="")
        print()
        
        # 打印数据
        for year in years:
            print(f"{year:<8}", end="")
            for indicator in indicators:
                value = processed_data[year].get(indicator, 'N/A')
                if value == 'N/A' or value is None:
                    print(f"{'N/A':<25}", end="")
                else:
                    print(f"{value:<25.2f}", end="")
            print()
        
        print("\n" + "="*80)
        print("数据验证完成")
        print("="*80 + "\n")
    
    def _validate_data(self, processed_data, stock_code):
        """
        数据验证：打印核心指标到控制台
        :param processed_data: 处理后的数据
        :param stock_code: 股票代码
        """
        print("\n" + "="*80)
        print(f"数据验证 - {stock_code}")
        print("="*80)
        
        # 打印公司信息
        if 'company_info' in processed_data:
            print("\n【公司信息】")
            for key, value in processed_data['company_info'].items():
                print(f"  {key}: {value}")
        
        # 打印估值指标
        if 'valuation_indicators' in processed_data:
            print("\n【估值指标】")
            for key, value in processed_data['valuation_indicators'].items():
                print(f"  {key}: {value}")
        
        # 打印财务指标
        if 'financial_indicators' in processed_data:
            print("\n【财务指标】")
            years = sorted(processed_data['financial_indicators'].keys())
            
            # 打印表头
            print(f"{'年份':<8}", end="")
            indicators = ['revenue', 'net_profit', 'roe', 'revenue_growth_rate', 'net_profit_growth_rate', 
                          'gross_margin', 'net_margin', 'net_profit_cash_ratio', 'debt_asset_ratio', 
                          'ocfps', 'bps', 'eps']
            for indicator in indicators:
                print(f"{indicator:<25}", end="")
            print()
            
            # 打印数据
            for year in years:
                print(f"{year:<8}", end="")
                for indicator in indicators:
                    value = processed_data['financial_indicators'][year].get(indicator, 'N/A')
                    if value == 'N/A' or value is None:
                        print(f"{'N/A':<25}", end="")
                    else:
                        print(f"{value:<25.2f}", end="")
                print()
        
        print("\n" + "="*80)
        print("数据验证完成")
        print("="*80 + "\n")
    
    def _calculate_investment_return(self, stock_code, processed_data):
        """
        计算投资收益复利
        
        Args:
            stock_code: 股票代码
            processed_data: 处理后的财务数据
            
        Returns:
            投资收益计算结果字典
        """
        try:
            logger.info(f"[Investment] 开始计算投资收益: {stock_code}")
            
            # 1. 获取分红数据
            dividend_data = self.spider.get_dividend_data(stock_code, years=[2020, 2021, 2022, 2023, 2024, 2025])
            
            if not dividend_data:
                logger.warning(f"[Investment] 未获取到分红数据")
                return None
            
            logger.info(f"[Investment] 获取到 {len(dividend_data)} 年分红数据")
            
            # 2. 获取初始价格（2019年底）
            initial_price = self.spider.get_initial_price(stock_code)
            
            if initial_price <= 0:
                logger.warning(f"[Investment] 未获取到初始价格，将使用第一次分红价格作为初始价格")
                # 不返回None，让InvestmentCalculator处理这种情况
            
            logger.info(f"[Investment] 初始价格: {initial_price}")
            
            # 3. 获取当前价格
            valuation_data = self.spider.get_eastmoney_valuation(stock_code)
            current_price = valuation_data.get('current_price', 0)
            
            if current_price <= 0:
                logger.warning(f"[Investment] 未获取到当前价格")
                return None
            
            logger.info(f"[Investment] 当前价格: {current_price}")
            
            # 4. 获取ROE数据
            roe_data = {}
            for year in [2020, 2021, 2022, 2023, 2024]:
                if year in processed_data and 'roe' in processed_data[year]:
                    roe_data[year] = processed_data[year]['roe']
            
            logger.info(f"[Investment] ROE数据: {roe_data}")
            
            # 5. 计算投资收益
            investment_result = self.investment_calculator.calculate_investment_return(
                dividend_data=dividend_data,
                initial_price=initial_price,
                current_price=current_price,
                roe_data=roe_data
            )
            
            logger.info(f"[Investment] 投资收益计算完成")
            logger.info(f"[Investment] 最终持股数: {investment_result['cumulative_shares'][-1] if investment_result['cumulative_shares'] else 0}")
            logger.info(f"[Investment] 最终累计收益率: {investment_result['cumulative_return'][-1] if investment_result['cumulative_return'] else 0}")
            
            return investment_result
            
        except Exception as e:
            logger.exception(f"[Investment] 计算投资收益失败: {e}")
            return None

def main():
    """
    主函数
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='生成财务报告Excel文件')
    
    # 添加参数
    parser.add_argument('-c', '--code', type=str, required=True, help='股票代码，如 SH600519')
    parser.add_argument('-o', '--output', type=str, help='输出文件路径')
    
    # 解析参数
    args = parser.parse_args()
    
    # 生成输出文件名
    if args.output:
        output_file = args.output
    else:
        # 默认输出文件名：财务数据分析-股票代码.xlsx
        output_file = f"财务数据分析-{args.code}.xlsx"
    
    print(f"正在生成 {args.code} 的财务报告...")
    print(f"输出文件: {output_file}")
    
    # 创建报告生成器
    generator = FinancialReportGenerator()
    
    # 生成报告
    if generator.generate_report(args.code, output_file):
        print(f"✅ 财务报告生成成功: {output_file}")
        print(f"📊 报告包含2020-2024年财务数据（多列格式）")
        print(f"📈 核心指标：ROE、净利润增长率、营收增长率、净利润含金量等")
        print(f"📋 已保存到：{os.path.abspath(output_file)}")
        print(f"🎯 数据填充方式：B列=2024, C列=2023, D列=2022, E列=2021, F列=2020")
    else:
        print("❌ 财务报告生成失败，请查看日志文件了解详情")
        print(f"日志文件: {LogConfig.LOG_FILE}")

if __name__ == "__main__":
    main()