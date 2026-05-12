import os
os.environ['NO_PROXY'] = '*' # 仅保留最基本的代理屏蔽

import streamlit as st
import akshare as ak
import pandas as pd
import time

st.set_page_config(page_title="多股资金对比看板", layout="wide")
st.title("📊 多股主力资金流向对比")
st.write("数据来源：东方财富网 (通过 AkShare 获取)")

# 输入多个代码
stock_inputs = st.text_input(
    "请输入股票代码（用英文逗号隔开）:", 
    value="002611, 600519, 000001, 002594"
)

@st.cache_data(ttl=3600)
def fetch_multiple_stocks(code_string):
    codes = [code.strip() for code in code_string.split(',') if code.strip()]
    results = []
    
    progress_bar = st.progress(0)
    
    for i, code in enumerate(codes):
        try:
            # 【关键修改】：避开全市场数据，精准获取单只股票信息，绝不触发防火墙！
            info_df = ak.stock_individual_info_em(symbol=code)
            
            # 从信息表中提取名称和市值
            name = info_df[info_df['item'] == '股票简称']['value'].values[0]
            market_cap_raw = info_df[info_df['item'] == '总市值']['value'].values[0]
            market_cap = float(market_cap_raw) / 1e8 # 转为亿元
            
            # 判断沪深市场前缀
            market_str = "sh" if code.startswith("6") else "sz"
            
            # 获取个股资金流向
            flow_df = ak.stock_individual_fund_flow(stock=code, market=market_str)
            flow_df = flow_df.sort_values(by='日期', ascending=False).reset_index(drop=True)
            
            # 计算近3/5/20日主力净流入 (单位转为亿元)
            inflow_3d = flow_df['主力净流入-净额'].head(3).sum() / 1e8
            inflow_5d = flow_df['主力净流入-净额'].head(5).sum() / 1e8
            inflow_20d = flow_df['主力净流入-净额'].head(20).sum() / 1e8
            
            results.append({
                "代码": code,
                "名称": name,
                "总市值(亿)": round(market_cap, 2),
                "3日净流入(亿)": round(inflow_3d, 2),
                "5日净流入(亿)": round(inflow_5d, 2),
                "20日净流入(亿)": round(inflow_20d, 2)
            })
            
        except Exception as e:
            st.warning(f"获取代码 {code} 的数据失败，请检查代码是否正确。")
            
        # 停顿 1 秒，礼貌请求
        time.sleep(1)
        progress_bar.progress((i + 1) / len(codes))
        
    return pd.DataFrame(results)

# 触发查询
if st.button("开始对比"):
    with st.spinner('正在逐个拉取数据，请稍候...'):
        df_result = fetch_multiple_stocks(stock_inputs)
        
        if not df_result.empty:
            st.success("🎉 数据拉取完成！")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("📝 数据汇总表")
                st.dataframe(df_result, use_container_width=True)
            with col2:
                st.subheader("📈 20日主力资金净流入对比")
                # 以名称为横坐标作图
                chart_data = df_result.set_index("名称")["20日净流入(亿)"]