import sys
import os

import streamlit as st
import io
import time
import pandas as pd
from main import FinancialReportGenerator
from excel_handler import ExcelHandler

# 设置页面配置
st.set_page_config(
    page_title="智库·全自动企业价值评估系统",
    page_icon="📊",
    layout="wide"
)

# 创建FinancialReportGenerator实例
generator = FinancialReportGenerator()

# 侧边栏配置
with st.sidebar:
    st.title("配置中心")
    
    # 授权校验模块
    st.subheader("授权校验")
    auth_code = st.text_input(
        "请输入授权码",
        placeholder="例如：ZHIKU888",
        type="password"
    )
    
    # 验证授权码
    authorized = auth_code == "SONG888"
    
    if authorized:
        st.success("✓ 授权成功")
        
        # API来源选择
        api_source = st.selectbox(
            "API 来源选择",
            options=["东方财富", "模拟数据"],
            index=0
        )
        
        # 报告年份范围
        st.write("报告年份范围")
        year_range = st.slider(
            "选择年份范围",
            min_value=2020,
            max_value=2024,
            value=(2020, 2024),
            step=1
        )
        
        # 调试模式开关
        debug_mode = st.checkbox("调试模式", value=False)
    else:
        st.error("✗ 授权失败")
        api_source = "东方财富"
        year_range = (2020, 2024)
        debug_mode = False

# 主界面
st.title("智库·全自动企业价值评估系统")

# 核心输入区
st.markdown("---")

# 授权检查
if authorized:
    st.subheader("企业价值分析")

    # 股票代码输入
    stock_code = st.text_input(
        "请输入股票代码",
        placeholder="例如：SH600089 或 600519",
        help="支持上海(SH)和深圳(SZ)股票代码"
    )

    # 分析按钮
    if st.button("开始深度分析", type="primary", use_container_width=True):
        if not stock_code:
            st.error("请输入有效的股票代码")
        else:
            # 规范化股票代码
            if not stock_code.startswith(('SH', 'SZ')):
                if len(stock_code) == 6:
                    # 智能市场识别
                    if stock_code.startswith(('00', '30', '002')):
                        # 深市股票
                        stock_code = f"SZ{stock_code}"
                    elif stock_code.startswith(('60', '68')):
                        # 沪市股票
                        stock_code = f"SH{stock_code}"
                    else:
                        st.error("请输入有效的6位股票代码")
                        st.stop()
                else:
                    st.error("请输入有效的6位股票代码")
                    st.stop()
            
            # 显示分析进度
            with st.status("正在进行深度分析...", expanded=True) as status:
                
                try:
                    # 1. 抓取数据
                    st.write("🔄 正在抓取财务数据...")
                    time.sleep(0.5)  # 模拟网络延迟
                    
                    # 获取财务数据
                    financial_data = generator.spider.get_company_financial_data(stock_code)
                    
                    st.write("📊 正在处理财务数据...")
                    time.sleep(0.5)
                    
                    # 处理财务数据
                    processed_data = generator.processor.process_financial_data_for_multicolumn(financial_data)
                    
                    # 2. 显示核心指标
                    st.write("✨ 正在生成分析结果...")
                    time.sleep(0.5)
                    
                    # 提取公司信息
                    company_info = processed_data.get('company_info', {})
                    
                    # 3. 生成Excel文件（内存流）
                    st.write("📈 正在生成Excel报告...")
                    time.sleep(0.5)
                    
                    # 创建ExcelHandler实例
                    excel_handler = ExcelHandler()
                    if excel_handler.create_new_workbook():
                        if excel_handler.write_multicolumn_data(processed_data, stock_code):
                            # 使用内存流保存Excel
                            output = excel_handler.save_to_memory()
                            if output is None:
                                st.error("生成Excel报告失败")
                                st.stop()
                            
                            status.update(label="分析完成！", state="complete", expanded=False)
                            
                            # 4. 核心看板
                            st.markdown("---")
                            st.subheader("核心指标看板")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                current_price = company_info.get('current_price', 0)
                                st.metric("当前股价", f"¥{current_price:.2f}")
                            
                            with col2:
                                total_market_cap = company_info.get('total_market_cap', 0)
                                st.metric("总市值", f"{total_market_cap:.2f} 亿")
                            
                            with col3:
                                cagr_5y = company_info.get('cagr_5y', 0)
                                if isinstance(cagr_5y, (int, float)):
                                    st.metric("5年复合增长率", f"{cagr_5y*100:.2f}%")
                                else:
                                    st.metric("5年复合增长率", "N/A")
                            
                            with col4:
                                # 获取最新年份的资产负债率
                                latest_year = 2024
                                debt_asset_ratio = processed_data.get(latest_year, {}).get('debt_asset_ratio', 0)
                                st.metric("资产负债率", f"{debt_asset_ratio*100:.2f}%")
                            
                            # 5. 数据审计结果
                            st.markdown("---")
                            with st.expander("🔍 数据审计结果", expanded=False):
                                st.write("### 年度数据完整性检查")
                                
                                # 检查2020-2024年数据完整性
                                missing_years = []
                                for year in range(2020, 2025):
                                    if year not in processed_data:
                                        missing_years.append(year)
                                    else:
                                        # 检查关键指标是否存在
                                        year_data = processed_data[year]
                                        missing_fields = []
                                        key_fields = ['net_profit', 'roe', 'revenue', 'gross_margin', 'net_margin']
                                        for field in key_fields:
                                            if field not in year_data or year_data[field] is None:
                                                missing_fields.append(field)
                                        
                                        if missing_fields:
                                            st.warning(f"⚠️ {year}年缺失关键指标: {', '.join(missing_fields)}")
                                
                                if missing_years:
                                    st.warning(f"⚠️ 缺失以下年份的数据: {', '.join(map(str, missing_years))}")
                                else:
                                    st.success("✅ 2020-2024年数据完整")
                                
                                # 检查CAGR计算状态
                                cagr_5y = company_info.get('cagr_5y', 'N/A')
                                if cagr_5y == 'N/A':
                                    st.warning("⚠️ CAGR计算: 起始年份或结束年份净利润为负数，增长率无数学意义")
                                elif isinstance(cagr_5y, (int, float)):
                                    st.success(f"✅ CAGR计算正常: {cagr_5y*100:.2f}%")
                            
                            # 6. 数据可视化
                            st.markdown("---")
                            st.subheader("数据趋势分析")
                            
                            # 准备图表数据
                            years = list(range(2020, 2025))
                            net_profit_data = []
                            roe_data = []
                            
                            for year in years:
                                year_data = processed_data.get(year, {})
                                net_profit_data.append(year_data.get('net_profit', 0))
                                roe_data.append(year_data.get('roe', 0))
                            
                            # 净利润趋势
                            st.write("### 净利润趋势（2020-2024）")
                            profit_df = pd.DataFrame({
                                '年份': years,
                                '净利润（亿元）': net_profit_data
                            })
                            st.line_chart(profit_df, x='年份', y='净利润（亿元）')
                            
                            # ROE趋势
                            st.write("### ROE趋势（2020-2024）")
                            roe_df = pd.DataFrame({
                                '年份': years,
                                'ROE（%）': [r*100 for r in roe_data]
                            })
                            st.line_chart(roe_df, x='年份', y='ROE（%）')
                            
                            # 6. 提供Excel下载
                            st.markdown("---")
                            st.subheader("报告下载")
                            
                            st.download_button(
                                label="💾 下载详细分析Excel报告",
                                data=output,
                                file_name=f"财务分析报告-{stock_code}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                            
                        else:
                            st.error("生成Excel报告失败")
                    else:
                        st.error("创建Excel工作簿失败")
                        
                except Exception as e:
                    st.error(f"分析过程中出现错误：{str(e)}")
                    if debug_mode:
                        st.exception(e)
else:
    st.error("智库专家系统：请联系管理员获取授权")

# 系统信息
st.markdown("---")
st.caption("© 2026 智库·全自动企业价值评估系统 | 数据来源：东方财富")
