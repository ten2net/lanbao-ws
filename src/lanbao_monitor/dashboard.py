"""
揽宝智能投研交易平台 - Web监控仪表板
基于 Streamlit 的实时监控界面
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(
    page_title="揽宝智能投研平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-online {
        color: #00cc00;
        font-weight: bold;
    }
    .status-offline {
        color: #cc0000;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def load_backtest_results():
    """加载回测结果"""
    results = []
    reports_dir = "/workspace/reports"
    if os.path.exists(reports_dir):
        for file in os.listdir(reports_dir):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(reports_dir, file), 'r') as f:
                        results.append(json.load(f))
                except Exception:
                    pass
    return results


def load_node_status():
    """加载节点状态（模拟数据）"""
    return {
        "market_data_node": {"status": "online", "last_update": datetime.now().strftime("%H:%M:%S")},
        "backtest_engine_node": {"status": "online", "last_update": datetime.now().strftime("%H:%M:%S")},
        "strategy_manager_node": {"status": "online", "last_update": datetime.now().strftime("%H:%M:%S")},
        "risk_control_node": {"status": "online", "last_update": datetime.now().strftime("%H:%M:%S")},
        "monitor_node": {"status": "online", "last_update": datetime.now().strftime("%H:%M:%S")},
    }


def main():
    # 标题
    st.markdown('<h1 class="main-header">📈 揽宝智能投研交易平台</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # 侧边栏
    with st.sidebar:
        st.image("https://via.placeholder.com/150x150.png?text=揽宝", width=150)
        st.title("导航菜单")
        
        page = st.radio(
            "选择页面",
            ["📊 系统概览", "📈 回测结果", "🔔 风险监控", "📋 节点状态", "⚙️ 系统配置"]
        )
        
        st.markdown("---")
        st.info("版本: v0.5.0 (MVP)")
        st.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 主内容区
    if page == "📊 系统概览":
        show_overview()
    elif page == "📈 回测结果":
        show_backtest_results()
    elif page == "🔔 风险监控":
        show_risk_monitor()
    elif page == "📋 节点状态":
        show_node_status()
    elif page == "⚙️ 系统配置":
        show_config()


def show_overview():
    """系统概览页面"""
    st.header("系统概览")
    
    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="在线节点数",
            value="5/5",
            delta="正常运行"
        )
    
    with col2:
        st.metric(
            label="今日回测数",
            value="12",
            delta="+3"
        )
    
    with col3:
        st.metric(
            label="活跃策略数",
            value="8",
            delta="+1"
        )
    
    with col4:
        st.metric(
            label="系统状态",
            value="🟢 正常",
            delta=None
        )
    
    st.markdown("---")
    
    # 系统资源使用
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("CPU 使用率")
        cpu_data = pd.DataFrame({
            '时间': pd.date_range(start='2024-01-01', periods=24, freq='H'),
            '使用率': np.random.uniform(20, 60, 24)
        })
        fig = go.Figure(go.Scatter(
            x=cpu_data['时间'],
            y=cpu_data['使用率'],
            fill='tozeroy',
            line=dict(color='#1f77b4')
        ))
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("内存 使用率")
        mem_data = pd.DataFrame({
            '时间': pd.date_range(start='2024-01-01', periods=24, freq='H'),
            '使用率': np.random.uniform(40, 70, 24)
        })
        fig = go.Figure(go.Scatter(
            x=mem_data['时间'],
            y=mem_data['使用率'],
            fill='tozeroy',
            line=dict(color='#ff7f0e')
        ))
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)


def show_backtest_results():
    """回测结果页面"""
    st.header("📈 回测结果分析")
    
    # 模拟回测数据
    backtest_data = pd.DataFrame({
        '回测ID': ['BT001', 'BT002', 'BT003', 'BT004', 'BT005'],
        '策略名称': ['MA交叉', 'RSI策略', '布林带', 'MACD', '双均线'],
        '总收益': [15.2, 8.5, -2.3, 12.1, 18.7],
        '年化收益': [18.5, 10.2, -3.1, 14.8, 22.3],
        '夏普比率': [1.45, 0.98, -0.25, 1.23, 1.67],
        '最大回撤': [-8.5, -12.3, -15.2, -9.8, -7.2],
        '交易次数': [45, 32, 28, 38, 52],
        '胜率': [62.5, 58.3, 45.2, 60.5, 65.8]
    })
    
    st.dataframe(backtest_data, use_container_width=True)
    
    st.markdown("---")
    
    # 收益对比图
    st.subheader("策略收益对比")
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='总收益',
        x=backtest_data['策略名称'],
        y=backtest_data['总收益'],
        marker_color='#1f77b4'
    ))
    fig.add_trace(go.Bar(
        name='年化收益',
        x=backtest_data['策略名称'],
        y=backtest_data['年化收益'],
        marker_color='#ff7f0e'
    ))
    
    fig.update_layout(
        barmode='group',
        height=400,
        yaxis_title='收益率 (%)',
        xaxis_title='策略'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 风险收益散点图
    st.subheader("风险-收益分析")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=abs(backtest_data['最大回撤']),
        y=backtest_data['年化收益'],
        mode='markers+text',
        text=backtest_data['策略名称'],
        textposition='top center',
        marker=dict(
            size=backtest_data['夏普比率'] * 10,
            color=backtest_data['夏普比率'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title='夏普比率')
        )
    ))
    
    fig.update_layout(
        height=400,
        xaxis_title='最大回撤 (%)',
        yaxis_title='年化收益 (%)'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def show_risk_monitor():
    """风险监控页面"""
    st.header("🔔 风险监控")
    
    # 风险指标
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("当前回撤", "-5.2%", "-0.5%")
    
    with col2:
        st.metric("风险敞口", "¥125,000", "+¥5,000")
    
    with col3:
        st.metric("在险价值(VaR)", "-3.8%", "正常")
    
    st.markdown("---")
    
    # 风险告警
    st.subheader("风险告警")
    
    alerts = [
        {"level": "高", "message": "策略 MA交叉 回撤超过10%", "time": "10:23:45"},
        {"level": "中", "message": "持仓集中度超过阈值", "time": "09:15:22"},
        {"level": "低", "message": "市场波动率上升", "time": "08:30:10"},
    ]
    
    for alert in alerts:
        color = {"高": "🔴", "中": "🟡", "低": "🟢"}[alert["level"]]
        st.warning(f"{color} [{alert['level']}风险] {alert['message']} - {alert['time']}")


def show_node_status():
    """节点状态页面"""
    st.header("📋 ROS2 节点状态")
    
    node_status = load_node_status()
    
    for node_name, status in node_status.items():
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**{node_name}**")
        
        with col2:
            status_color = "status-online" if status["status"] == "online" else "status-offline"
            st.markdown(f'<span class="{status_color}">● {status["status"].upper()}</span>', 
                       unsafe_allow_html=True)
        
        with col3:
            st.write(f"更新: {status['last_update']}")
    
    st.markdown("---")
    
    # 日志查看
    st.subheader("节点日志")
    log_filter = st.selectbox("选择节点", list(node_status.keys()))
    
    logs = """
    [INFO] 2024-01-15 10:23:45 - Node initialized successfully
    [INFO] 2024-01-15 10:23:46 - Connected to ROS2 daemon
    [INFO] 2024-01-15 10:24:00 - Processing market data...
    [INFO] 2024-01-15 10:24:15 - Strategy execution completed
    """
    st.code(logs, language='bash')


def show_config():
    """系统配置页面"""
    st.header("⚙️ 系统配置")
    
    with st.form("config_form"):
        st.subheader("回测配置")
        initial_capital = st.number_input("初始资金", value=100000, step=10000)
        commission_rate = st.number_input("手续费率", value=0.0003, step=0.0001, format="%.4f")
        slippage = st.number_input("滑点", value=0.001, step=0.0001, format="%.4f")
        
        st.subheader("风险控制")
        max_drawdown = st.slider("最大回撤限制 (%)", 0, 50, 20)
        position_limit = st.slider("持仓限制 (%)", 0, 100, 80)
        
        submitted = st.form_submit_button("保存配置")
        if submitted:
            st.success("配置已保存！")


if __name__ == "__main__":
    main()
