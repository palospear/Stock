import streamlit as st
import akshare as ak
import pandas as pd

# 设置网页基本信息
st.set_page_config(page_title="个股资金流向看板", layout="centered")
st.title("📈 个股资金流向与市值占比")

# 输入交互区
stock_code = st.text_input("请输入 6 位股票代码 (例如截图中的东方精工：002611):", value="002611")

# 将获取数据的函数缓存起来，防止每次点击页面刷新都重新向服务器请求数据导致被封 IP
@st.cache_data(ttl=3600)
def fetch_fund_flow_data(code):
    try:
        # 1. 获取实时行情，提取总市值
        spot_df = ak.stock_zh_a_spot_em()
        stock_info = spot_df[spot_df['代码'] == code]
        
        if stock_info.empty:
            return None, "未找到该股票代码，请检查是否输入正确。"
            
        name = stock_info['名称'].values[0]
        # AkShare 抓取的市值默认单位通常是“元”
        market_cap = stock_info['总市值'].values[0] 
        
        # 2. 判断市场前缀 (6开头为沪市 sh，其余通常视作深市 sz)
        market_str = "sh" if code.startswith("6") else "sz"
        
        # 3. 获取个股资金流向历史数据
        flow_df = ak.stock_individual_fund_flow(stock=code, market=market_str)
        
        # 按“日期”降序排列，确保最新的交易日在第一行
        flow_df = flow_df.sort_values(by='日期', ascending=False).reset_index(drop=True)
        
        # 4. 计算近 3/5/20 日的主力资金净流入总额 (单位：元)
        inflow_3d = flow_df['主力净流入-净额'].head(3).sum()
        inflow_5d = flow_df['主力净流入-净额'].head(5).sum()
        inflow_20d = flow_df['主力净流入-净额'].head(20).sum()
        
        return {
            "name": name,
            "market_cap": market_cap,
            "inflow_3d": inflow_3d,
            "inflow_5d": inflow_5d,
            "inflow_20d": inflow_20d,
            "history_df": flow_df[['日期', '收盘价', '主力净流入-净额', '超大单净流入-净额', '大单净流入-净额']].head(20)
        }, None
        
    except Exception as e:
        return None, f"获取数据失败，请稍后重试。错误信息: {e}"

# 当用户点击按钮时触发查询
if st.button("查询资金流向"):
    with st.spinner('正在从 AkShare 努力拉取数据...'):
        data, err = fetch_fund_flow_data(stock_code)
        
        if err:
            st.error(err)
        else:
            st.write("---")
            st.subheader(f"📊 {data['name']} ({stock_code}) 数据展示")
            
            # 将数值从“元”转换为“亿”，方便阅读（与同花顺/涨乐财富通一致）
            mc_yi = data['market_cap'] / 1e8
            in3_yi = data['inflow_3d'] / 1e8
            in5_yi = data['inflow_5d'] / 1e8
            in20_yi = data['inflow_20d'] / 1e8
            
            # 计算占总市值的百分比
            ratio_3d = (data['inflow_3d'] / data['market_cap']) * 100
            ratio_5d = (data['inflow_5d'] / data['market_cap']) * 100
            ratio_20d = (data['inflow_20d'] / data['market_cap']) * 100
            
            # 顶部展示总市值
            st.metric(label="当前总市值", value=f"{mc_yi:.2f} 亿")
            
            # 分三列展示 3日、5日、20日数据
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(label="3日主力净流入", value=f"{in3_yi:.2f} 亿", 
                          delta=f"占总市值: {ratio_3d:.3f}%", delta_color="off")
            with col2:
                st.metric(label="5日主力净流入", value=f"{in5_yi:.2f} 亿", 
                          delta=f"占总市值: {ratio_5d:.3f}%", delta_color="off")
            with col3:
                st.metric(label="20日主力净流入", value=f"{in20_yi:.2f} 亿", 
                          delta=f"占总市值: {ratio_20d:.3f}%", delta_color="off")
            
            st.write("---")
            st.write("📝 **近 20 日资金明细数据 (单位：元)**")
            # 展示数据表格
            st.dataframe(data['history_df'], use_container_width=True)
