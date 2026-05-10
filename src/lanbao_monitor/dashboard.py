"""
揽宝智能投研交易平台 - Web监控仪表板
基于 Streamlit 的实时监控界面，接入真实 ROS2 话题数据
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import subprocess
import sys
import psutil
from datetime import datetime

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
    .status-error {
        color: #ff8800;
        font-weight: bold;
    }
    .status-init {
        color: #888888;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def _get_project_root():
    """获取项目根目录"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run_ros2_client(cmd: str = "nodes", arg: str = ""):
    """运行 ROS2 客户端脚本获取数据

    Args:
        cmd: 命令类型 (nodes/stats/quality/sync)
        arg: 命令参数
    """
    project_root = _get_project_root()
    script = os.path.join(
        project_root, "src", "lanbao_monitor", "lanbao_monitor", "ros2_client.py"
    )

    if not os.path.exists(script):
        return {"error": f"ros2_client.py 不存在: {script}"}

    env = os.environ.copy()
    # 添加 ROS2 和项目路径
    pp = env.get("PYTHONPATH", "")
    ros_pp = "/opt/ros/humble/lib/python3.10/site-packages:/opt/ros/humble/local/lib/python3.10/dist-packages"
    project_pp = ":".join([
        f"{project_root}/src/lanbao_monitor",
        f"{project_root}/install/lanbao_interfaces/lib/python3.10/site-packages",
        f"{project_root}/install/lanbao_core/lib/python3.10/site-packages",
        f"{project_root}/build/lanbao_interfaces",
        f"{project_root}/build/lanbao_core",
    ])
    env["PYTHONPATH"] = f"{project_pp}:{ros_pp}:{pp}" if pp else f"{project_pp}:{ros_pp}"

    ld = env.get("LD_LIBRARY_PATH", "")
    ros_ld = "/opt/ros/humble/lib/x86_64-linux-gnu:/opt/ros/humble/lib"
    project_ld = f"{project_root}/install/lanbao_interfaces/lib"
    env["LD_LIBRARY_PATH"] = f"{project_ld}:{ros_ld}:{ld}" if ld else f"{project_ld}:{ros_ld}"

    try:
        args = [sys.executable, script, cmd]
        if arg:
            args.append(arg)
        result = subprocess.run(
            args,
            capture_output=True, text=True, timeout=15,
            env=env, cwd=project_root
        )
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": f"解析失败: {result.stdout[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _format_timestamp(ts_ms):
    """将毫秒时间戳格式化为可读字符串"""
    if not ts_ms:
        return "—"
    try:
        return datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts_ms)


def load_system_metrics_history(max_points: int = 60):
    """加载系统 CPU/内存 历史使用率，通过 session_state 维护时间序列

    Args:
        max_points: 最多保留的数据点数量

    Returns:
        (cpu_df, mem_df) 两个 DataFrame，包含真实历史数据
    """
    # 初始化 session_state
    if "sys_metrics_history" not in st.session_state:
        st.session_state.sys_metrics_history = {
            "timestamps": [],
            "cpu_values": [],
            "mem_values": [],
        }

    history = st.session_state.sys_metrics_history

    # 获取当前真实系统指标
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
        mem_percent = psutil.virtual_memory().percent
    except Exception:
        cpu_percent = 0.0
        mem_percent = 0.0

    now = datetime.now()
    history["timestamps"].append(now)
    history["cpu_values"].append(cpu_percent)
    history["mem_values"].append(mem_percent)

    # 滚动窗口：只保留最近 max_points 个数据点
    if len(history["timestamps"]) > max_points:
        history["timestamps"] = history["timestamps"][-max_points:]
        history["cpu_values"] = history["cpu_values"][-max_points:]
        history["mem_values"] = history["mem_values"][-max_points:]

    cpu_df = pd.DataFrame({
        "时间": history["timestamps"],
        "使用率": history["cpu_values"],
    })
    mem_df = pd.DataFrame({
        "时间": history["timestamps"],
        "使用率": history["mem_values"],
    })
    return cpu_df, mem_df


def load_node_status():
    """从 ROS2 服务加载真实节点状态"""
    data = _run_ros2_client("nodes")
    if data.get("success"):
        return {
            s["node_name"]: {
                "status": s["status"],
                "node_type": s["node_type"],
                "cpu_usage": s["cpu_usage"],
                "memory_usage": s["memory_usage"],
                "message_count": s["message_count"],
                "last_error": s["last_error"],
                "timestamp": s["timestamp"],
                "last_update": _format_timestamp(s["timestamp"]),
            }
            for s in data["statuses"]
        }
    return {}


def load_data_stats():
    """从 ROS2 服务加载数据概况"""
    data = _run_ros2_client("stats")
    return data.get("stats") if data.get("success") else None


def load_data_quality():
    """从 ROS2 服务加载数据质量"""
    data = _run_ros2_client("quality")
    return data.get("items") if data.get("success") else None


def load_sync_status():
    """从 ROS2 服务加载同步状态"""
    data = _run_ros2_client("sync")
    return data.get("detail") if data.get("success") else None


def load_alerts():
    """从 MonitorNode 持久化文件加载系统告警"""
    alerts_file = os.environ.get("LANBAO_ALERTS_FILE", "./data/alerts.json")
    alerts_file = os.path.expanduser(alerts_file)
    if not os.path.exists(alerts_file):
        return []
    try:
        with open(alerts_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def load_backtest_results():
    """加载回测结果 — 从项目根目录的 reports/ 文件夹读取"""
    results = []
    debug_info = []
    # 基于项目根目录的绝对路径，避免工作目录不一致导致找不到文件
    project_root = _get_project_root()
    reports_dirs = [
        os.path.join(project_root, "reports"),
        os.environ.get("LANBAO_REPORTS_DIR", ""),
        "./reports",
        "/workspace/reports",
    ]
    for reports_dir in reports_dirs:
        if not reports_dir:
            continue
        reports_dir = os.path.expanduser(reports_dir)
        debug_info.append(f"检查目录: {reports_dir}")
        if os.path.exists(reports_dir) and os.path.isdir(reports_dir):
            files = [f for f in os.listdir(reports_dir) if f.endswith(".json")]
            debug_info.append(f"  -> 找到 {len(files)} 个 JSON 文件: {files}")
            for file in sorted(files, reverse=True):
                try:
                    filepath = os.path.join(reports_dir, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        results.append(json.load(f))
                except Exception as e:
                    debug_info.append(f"  -> 读取失败 {file}: {e}")
        else:
            debug_info.append(f"  -> 目录不存在")
    return results, debug_info


def get_status_color_class(status):
    """根据状态返回 CSS 类名"""
    return {
        "RUNNING": "status-online",
        "ONLINE": "status-online",
        "ERROR": "status-error",
        "INITIALIZING": "status-init",
        "STOPPED": "status-offline",
        "OFFLINE": "status-offline",
    }.get(status, "status-offline")


def get_status_emoji(status):
    """根据状态返回表情符号"""
    return {
        "RUNNING": "🟢",
        "ONLINE": "🟢",
        "ERROR": "🟠",
        "INITIALIZING": "⚪",
        "STOPPED": "🔴",
        "OFFLINE": "🔴",
    }.get(status, "⚫")


def main():
    # 标题
    st.markdown('<h1 class="main-header">📈 揽宝智能投研交易平台</h1>', unsafe_allow_html=True)
    st.markdown("---")

    # 侧边栏
    with st.sidebar:
        st.title("导航菜单")

        page = st.radio(
            "选择页面",
            ["🏠 系统概览", "🗄️ 数据底座", "📈 回测结果", "🔔 风险监控", "📋 节点状态", "⚙️ 系统配置"]
        )

        st.markdown("---")
        st.info("版本: v0.5.0 (MVP)")
        st.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 刷新按钮
        if st.button("🔄 刷新数据"):
            st.rerun()

    # 主内容区
    if page == "🏠 系统概览":
        show_overview()
    elif page == "🗄️ 数据底座":
        show_data_monitor()
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

    node_status = load_node_status()

    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)

    online_count = sum(
        1 for s in node_status.values() if s["status"] in ("RUNNING", "ONLINE")
    )
    total_count = len(node_status)

    with col1:
        st.metric(
            label="在线节点数",
            value=f"{online_count}/{total_count}" if total_count else "—",
            delta="正常运行" if online_count == total_count and total_count > 0 else "有节点异常" if total_count else None
        )

    with col2:
        backtests = load_backtest_results()
        st.metric(
            label="回测报告数",
            value=str(len(backtests)),
            delta=None
        )

    with col3:
        alerts = load_alerts()
        critical = sum(1 for a in alerts if a.get("type") == "CRITICAL")
        st.metric(
            label="未处理告警",
            value=str(len(alerts[-20:])),
            delta=f"{critical} 严重" if critical else None,
            delta_color="inverse" if critical else "normal"
        )

    with col4:
        system_ok = total_count > 0 and online_count == total_count and not critical
        st.metric(
            label="系统状态",
            value="🟢 正常" if system_ok else "🟠 异常" if total_count else "⚪ 未连接",
            delta=None
        )

    st.markdown("---")

    # 节点资源使用
    if node_status:
        st.subheader("节点资源概览")
        df_data = []
        for name, s in node_status.items():
            df_data.append({
                "节点": name,
                "状态": s["status"],
                "CPU (%)": round(s["cpu_usage"], 2) if s["cpu_usage"] else "—",
                "内存 (%)": round(s["memory_usage"], 2) if s["memory_usage"] else "—",
                "消息数": s["message_count"] if s["message_count"] else "—",
                "最后更新": s["last_update"],
            })
        st.dataframe(pd.DataFrame(df_data), use_container_width=True)
    else:
        st.warning("未获取到节点状态数据。请确保 monitor_node 已启动，且 ROS2 环境已正确配置。")

    # 系统资源使用 — 真实数据
    cpu_df, mem_df = load_system_metrics_history()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("CPU 使用率")
        if len(cpu_df) > 1:
            fig = go.Figure(go.Scatter(
                x=cpu_df['时间'],
                y=cpu_df['使用率'],
                fill='tozeroy',
                line=dict(color='#1f77b4'),
                hovertemplate='时间: %{x|%H:%M:%S}<br>CPU: %{y:.1f}%<extra></extra>',
            ))
            fig.update_layout(
                height=250,
                margin=dict(l=20, r=20, t=20, b=20),
                yaxis=dict(range=[0, 100], title='使用率 (%)'),
                xaxis_title=None,
            )
            st.plotly_chart(fig, key="cpu_chart", use_container_width=True)
        else:
            st.info("刷新页面以收集 CPU 历史数据")

    with col2:
        st.subheader("内存 使用率")
        if len(mem_df) > 1:
            fig = go.Figure(go.Scatter(
                x=mem_df['时间'],
                y=mem_df['使用率'],
                fill='tozeroy',
                line=dict(color='#ff7f0e'),
                hovertemplate='时间: %{x|%H:%M:%S}<br>内存: %{y:.1f}%<extra></extra>',
            ))
            fig.update_layout(
                height=250,
                margin=dict(l=20, r=20, t=20, b=20),
                yaxis=dict(range=[0, 100], title='使用率 (%)'),
                xaxis_title=None,
            )
            st.plotly_chart(fig, key="mem_chart", use_container_width=True)
        else:
            st.info("刷新页面以收集内存历史数据")


def _run_backtest_ros2(strategy_id: str, symbol: str, start_date: str, end_date: str):
    """通过 ROS2 服务调用运行回测

    Returns:
        dict: {success, backtest_id, message, stdout, stderr, returncode}
    """
    project_root = _get_project_root()
    env = os.environ.copy()
    pp = env.get("PYTHONPATH", "")
    ros_pp = "/opt/ros/humble/lib/python3.10/site-packages:/opt/ros/humble/local/lib/python3.10/dist-packages"
    project_pp = ":".join([
        f"{project_root}/src/lanbao_backtest",
        f"{project_root}/install/lanbao_interfaces/lib/python3.10/site-packages",
        f"{project_root}/install/lanbao_core/lib/python3.10/site-packages",
        f"{project_root}/build/lanbao_interfaces",
        f"{project_root}/build/lanbao_core",
    ])
    env["PYTHONPATH"] = f"{project_pp}:{ros_pp}:{pp}" if pp else f"{project_pp}:{ros_pp}"

    ld = env.get("LD_LIBRARY_PATH", "")
    ros_ld = "/opt/ros/humble/lib/x86_64-linux-gnu:/opt/ros/humble/lib"
    project_ld = f"{project_root}/install/lanbao_interfaces/lib"
    env["LD_LIBRARY_PATH"] = f"{project_ld}:{ros_ld}:{ld}" if ld else f"{project_ld}:{ros_ld}"

    script = os.path.join(project_root, "src", "lanbao_backtest", "lanbao_backtest", "backtest_cli.py")
    if not os.path.exists(script):
        return {
            "success": False,
            "message": f"backtest_cli.py 不存在: {script}",
            "stdout": "", "stderr": "", "returncode": -1
        }

    try:
        result = subprocess.run(
            [sys.executable, script, strategy_id, symbol, start_date, end_date],
            capture_output=True, text=True, timeout=120,
            env=env, cwd=project_root
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # 先尝试从 stdout 解析 JSON
        if stdout:
            try:
                parsed = json.loads(stdout)
                parsed["stdout"] = stdout
                parsed["stderr"] = stderr
                parsed["returncode"] = result.returncode
                return parsed
            except json.JSONDecodeError:
                pass

        # 如果 stdout 不是 JSON，构造错误响应
        return {
            "success": False,
            "message": f"CLI 返回非 JSON 输出 (exit={result.returncode}): {stdout[:300]}",
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "回测调用超时（超过120秒），请检查 backtest_engine_node 是否卡住",
            "stdout": "", "stderr": "", "returncode": -1
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"回测调用异常: {str(e)}",
            "stdout": "", "stderr": "", "returncode": -1
        }


def show_backtest_results():
    """回测结果页面 — 展示真实回测数据，支持在线运行回测"""
    st.header("📈 回测结果分析")

    # ========== 在线回测执行区 ==========
    with st.expander("▶️ 运行新回测", expanded=False):
        st.subheader("配置回测参数")
        col1, col2, col3 = st.columns(3)
        with col1:
            strategy = st.selectbox("策略", ["ma_cross", "rsi"], index=0)
        with col2:
            symbol = st.text_input("股票代码", value="000001.SZ")
        with col3:
            end = datetime.now()
            start = end.replace(year=end.year - 1)
            start_date = st.date_input("开始日期", value=start)
            end_date = st.date_input("结束日期", value=end)

        # 初始化 session state
        if "backtest_state" not in st.session_state:
            st.session_state.backtest_state = "idle"
        if "backtest_result" not in st.session_state:
            st.session_state.backtest_result = None

        # 如果有已完成的回测结果，显示在表单下方
        if st.session_state.backtest_state == "completed" and st.session_state.backtest_result:
            r = st.session_state.backtest_result
            st.success(f"✅ 回测完成！ID: {r.get('backtest_id')}")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**策略**: {r.get('strategy_id', strategy)}")
                st.write(f"**标的**: {symbol}")
            with col_b:
                st.write(f"**消息**: {r.get('message', '')}")
            if st.button("🔄 清除并运行新回测"):
                st.session_state.backtest_state = "idle"
                st.session_state.backtest_result = None
                st.rerun()

        elif st.session_state.backtest_state == "failed" and st.session_state.backtest_result:
            r = st.session_state.backtest_result
            st.error(f"❌ 回测失败: {r.get('message', '未知错误')}")
            with st.expander("查看调试信息"):
                st.text(f"returncode: {r.get('returncode')}")
                if r.get('stdout'):
                    st.text("STDOUT:")
                    st.code(r['stdout'])
                if r.get('stderr'):
                    st.text("STDERR:")
                    st.code(r['stderr'])
            st.info("请确保以下节点已启动: backtest_engine_node, market_data_node")
            if st.button("🔄 重试"):
                st.session_state.backtest_state = "idle"
                st.session_state.backtest_result = None
                st.rerun()

        # 启动按钮
        if st.session_state.backtest_state in ("idle", "failed"):
            if st.button("🚀 启动回测", type="primary"):
                st.session_state.backtest_state = "running"
                st.session_state.backtest_result = None
                st.rerun()

        # 执行回测（在单独的 status 容器中显示进度）
        if st.session_state.backtest_state == "running":
            with st.status("⏳ 回测执行中...", expanded=True) as status:
                st.write("1️⃣ 初始化 ROS2 客户端...")
                st.write("2️⃣ 连接 backtest/run 服务...")
                st.write("3️⃣ 请求获取历史行情数据...")
                st.write("4️⃣ 执行回测计算（可能耗时较长）...")
                st.write("5️⃣ 保存结果...")

                result = _run_backtest_ros2(
                    strategy,
                    symbol,
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d")
                )

                st.session_state.backtest_result = result

                if result.get("success"):
                    st.session_state.backtest_state = "completed"
                    status.update(label="✅ 回测完成！", state="complete", expanded=False)
                    st.rerun()
                else:
                    st.session_state.backtest_state = "failed"
                    status.update(label=f"❌ 回测失败", state="error", expanded=True)
                    st.rerun()

    st.markdown("---")

    # ========== 回测结果列表 ==========
    results, debug_info = load_backtest_results()

    with st.expander("🔍 诊断信息"):
        st.write("**回测结果加载诊断**")
        for line in debug_info:
            st.text(line)
        st.write(f"**加载到的记录数**: {len(results)}")

    if results:
        # 从真实 JSON 数据构建 DataFrame
        df_data = []
        for r in results:
            df_data.append({
                "回测ID": r.get("backtest_id", "—"),
                "策略名称": r.get("strategy_name", r.get("strategy_id", "—")),
                "标的": r.get("symbol", "—"),
                "总收益 (%)": r.get("total_return", "—"),
                "年化收益 (%)": r.get("annual_return", "—"),
                "夏普比率": r.get("sharpe_ratio", "—"),
                "最大回撤 (%)": r.get("max_drawdown", "—"),
                "交易次数": r.get("trade_count", "—"),
                "胜率 (%)": r.get("win_rate", "—"),
            })
        st.dataframe(pd.DataFrame(df_data), use_container_width=True)
    else:
        st.info("暂无回测报告。请通过上方 '▶️ 运行新回测' 执行回测，或使用命令行运行。")

    st.markdown("---")

    # ========== 收益对比图（真实数据）==========
    st.subheader("策略收益对比")

    if results:
        names = [r.get("strategy_name", r.get("strategy_id", "—")) for r in results]
        total_returns = [r.get("total_return", 0) for r in results]
        annual_returns = [r.get("annual_return", 0) for r in results]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='总收益',
            x=names,
            y=total_returns,
            marker_color='#1f77b4'
        ))
        fig.add_trace(go.Bar(
            name='年化收益',
            x=names,
            y=annual_returns,
            marker_color='#ff7f0e'
        ))

        fig.update_layout(
            barmode='group',
            height=400,
            yaxis_title='收益率 (%)',
            xaxis_title='策略'
        )

        st.plotly_chart(fig, key="returns_chart", use_container_width=True)
    else:
        st.info("📊 暂无回测数据，运行回测后将在此显示策略收益对比图。")

    st.markdown("---")

    # ========== 风险收益散点图（真实数据）==========
    st.subheader("风险-收益分析")

    if results:
        names = [r.get("strategy_name", r.get("strategy_id", "—")) for r in results]
        annual_returns = [r.get("annual_return", 0) for r in results]
        drawdowns = [abs(r.get("max_drawdown", 0)) for r in results]
        sharpe_values = [r.get("sharpe_ratio", 0) for r in results]
        marker_sizes = [abs(s) * 10 + 5 for s in sharpe_values]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=drawdowns,
            y=annual_returns,
            mode='markers+text',
            text=names,
            textposition='top center',
            hovertemplate='策略: %{text}<br>最大回撤: %{x:.2f}%<br>年化收益: %{y:.2f}%<extra></extra>',
            marker=dict(
                size=marker_sizes,
                color=sharpe_values,
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

        st.plotly_chart(fig, key="risk_return_chart", use_container_width=True)
    else:
        st.info("📈 暂无回测数据，运行回测后将在此显示风险-收益散点图。")

    st.markdown("---")

    # ========== 单个回测详情展开 ==========
    st.subheader("回测详情")

    if results:
        project_root = _get_project_root()
        for r in results:
            strategy_display = r.get('strategy_name', r.get('strategy_id', '—'))
            with st.expander(f"📄 {r.get('backtest_id', '—')} — {strategy_display} ({r.get('symbol', '—')})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**回测周期**: {r.get('start_date', '—')} ~ {r.get('end_date', '—')}")
                    st.write(f"**总收益**: {r.get('total_return', '—')} %")
                    st.write(f"**年化收益**: {r.get('annual_return', '—')} %")
                    st.write(f"**夏普比率**: {r.get('sharpe_ratio', '—')}")
                with col2:
                    st.write(f"**最大回撤**: {r.get('max_drawdown', '—')} %")
                    st.write(f"**波动率**: {r.get('volatility', '—')} %")
                    st.write(f"**交易次数**: {r.get('trade_count', '—')}")
                    st.write(f"**胜率**: {r.get('win_rate', '—')} %")

                html_file = os.path.join(project_root, "reports", f"{r.get('backtest_id')}.html")
                if os.path.exists(html_file):
                    with open(html_file, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    st.components.v1.html(html_content, height=600, scrolling=True)
                else:
                    st.caption("HTML 报告文件未找到")
    else:
        st.info("📋 暂无回测详情，运行回测后将在此显示每条回测的详细报告。")


def show_risk_monitor():
    """风险监控页面"""
    st.header("🔔 风险监控")

    alerts = load_alerts()

    # 风险指标
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("当前告警数", str(len(alerts)))

    with col2:
        critical_count = sum(1 for a in alerts if a.get("type") == "CRITICAL")
        st.metric("严重告警", str(critical_count))

    with col3:
        warning_count = sum(1 for a in alerts if a.get("type") == "WARNING")
        st.metric("警告告警", str(warning_count))

    st.markdown("---")

    # 风险告警列表
    st.subheader("风险告警")

    if alerts:
        # 按时间倒序显示最近 50 条
        for alert in reversed(alerts[-50:]):
            level = alert.get("type", "INFO")
            color = {"CRITICAL": "🔴", "ERROR": "🔴", "WARNING": "🟡", "INFO": "🟢"}.get(level, "⚪")
            ts = _format_timestamp(alert.get("timestamp"))
            component = alert.get("component", "未知")
            message = alert.get("message", "")
            st.warning(f"{color} [{level}] [{component}] {message} — {ts}")
    else:
        st.info("暂无告警数据。告警将由 MonitorNode 自动收集并持久化到 data/alerts.json。")


def show_node_status():
    """节点状态页面 — 展示真实 ROS2 节点状态"""
    st.header("📋 ROS2 节点状态")

    node_status = load_node_status()

    if not node_status:
        st.warning("未获取到节点状态。请检查：\n1. monitor_node 是否已启动\n2. ROS2 环境是否正确配置\n3. 其他节点是否已启动并发布状态")
        return

    # 节点状态表格
    for node_name, status in node_status.items():
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

        with col1:
            st.write(f"**{node_name}**")
            st.caption(f"类型: {status['node_type'] or '—'}")

        with col2:
            emoji = get_status_emoji(status["status"])
            css_class = get_status_color_class(status["status"])
            st.markdown(
                f'<span class="{css_class}">{emoji} {status["status"]}</span>',
                unsafe_allow_html=True
            )

        with col3:
            cpu = f"{status['cpu_usage']:.1f}%" if status["cpu_usage"] else "—"
            mem = f"{status['memory_usage']:.1f}%" if status["memory_usage"] else "—"
            st.write(f"CPU: {cpu}")
            st.write(f"内存: {mem}")

        with col4:
            st.write(f"消息: {status['message_count'] or '—'}")

        with col5:
            st.write(f"更新: {status['last_update']}")
            if status["last_error"]:
                st.error(f"错误: {status['last_error']}")

        st.divider()

    # 原始 JSON 数据（可折叠）
    with st.expander("查看原始数据"):
        st.json(node_status)


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


def show_data_monitor():
    """数据底座监控页面 — 展示 DuckDB 数据概况、同步状态、数据质量"""
    st.header("🗄️ 数据底座监控")

    # 加载数据
    stats = load_data_stats()
    quality_items = load_data_quality()
    sync_detail = load_sync_status()

    if not stats:
        st.warning("未获取到数据概况。请检查：\n1. data_sync_node 是否已启动\n2. DuckDB 数据库是否存在\n3. ROS2 环境是否正确配置")
        return

    # ========== 顶部概览卡片 ==========
    st.subheader("数据概况")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="总记录数",
            value=f"{stats['total_records']:,}"
        )
    with col2:
        st.metric(
            label="覆盖股票",
            value=f"{stats['total_symbols']:,} 只"
        )
    with col3:
        st.metric(
            label="日期范围",
            value=f"{stats['start_date']} ~ {stats['end_date']}"
        )
    with col4:
        st.metric(
            label="数据库大小",
            value=f"{stats['db_size_mb']:.1f} MB"
        )

    st.markdown("---")

    # ========== 第二行：交易所分布 + 同步状态 ==========
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("交易所分布")
        if stats.get("exchange_names") and stats.get("exchange_counts"):
            fig = go.Figure(data=[go.Pie(
                labels=stats["exchange_names"],
                values=stats["exchange_counts"],
                hole=0.4,
                textinfo="label+percent",
                marker=dict(colors=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"])
            )])
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20), showlegend=False)
            st.plotly_chart(fig, key="exchange_pie", use_container_width=True)

            # 明细表格
            df_ex = pd.DataFrame({
                "交易所": stats["exchange_names"],
                "股票数": stats["exchange_counts"],
            })
            df_ex["占比"] = (df_ex["股票数"] / df_ex["股票数"].sum() * 100).round(1).astype(str) + "%"
            st.dataframe(df_ex, use_container_width=True, hide_index=True)
        else:
            st.info("暂无交易所分布数据")

    with col_right:
        st.subheader("数据同步状态")
        if sync_detail:
            status_color = {
                "completed": "🟢",
                "idle": "🟢",
                "running": "🔵",
                "failed": "🔴",
            }.get(sync_detail.get("status"), "⚪")
            st.write(f"**状态**: {status_color} {sync_detail.get('status', 'unknown').upper()}")
            st.write(f"**上次同步**: {sync_detail.get('last_sync_time', '—')}")
            st.write(f"**成功 / 总计**: {sync_detail.get('success_count', 0)} / {sync_detail.get('total_symbols', 0)}")
            st.write(f"**失败**: {sync_detail.get('failed_count', 0)}")
            st.write(f"**耗时**: {sync_detail.get('duration_seconds', 0):.1f} 秒")
            if sync_detail.get("message"):
                st.caption(f"消息: {sync_detail['message']}")

            # 进度条
            total = sync_detail.get("total_symbols", 0)
            if total > 0:
                progress = sync_detail.get("success_count", 0) / total
                st.progress(progress, text=f"同步进度: {progress*100:.1f}%")
        else:
            st.info("暂无同步状态数据")

    st.markdown("---")

    # ========== 第三行：数据质量 + 新鲜度 ==========
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("数据质量检查")
        if quality_items:
            # 计算综合评分
            total_checks = len(quality_items)
            pass_checks = sum(1 for item in quality_items if item["status"] == "PASS")
            warning_checks = sum(1 for item in quality_items if item["status"] == "WARNING")
            score = int((pass_checks + warning_checks * 0.5) / total_checks * 100)

            score_color = "🟢" if score >= 90 else "🟡" if score >= 70 else "🔴"
            st.write(f"**综合评分**: {score_color} {score}/100")

            # 质量检查明细表格
            df_q = pd.DataFrame(quality_items)
            df_q["结果"] = df_q["status"].map({
                "PASS": "✅ 通过",
                "WARNING": "⚠️ 警告",
                "FAIL": "❌ 失败"
            })
            st.dataframe(
                df_q[["check_name", "结果", "description"]].rename(
                    columns={"check_name": "检查项", "description": "详情"}
                ),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("暂无数据质量数据")

    with col_right:
        st.subheader("数据新鲜度")
        if stats.get("end_date"):
            latest_date = stats["end_date"]
            st.write(f"**最新数据日期**: {latest_date}")

            # 计算距离今天的天数
            try:
                from datetime import date as dt_date
                latest = dt_date.fromisoformat(latest_date)
                today = dt_date.today()
                days_behind = (today - latest).days
                if days_behind == 0:
                    st.success("数据已更新到最新交易日 ✅")
                elif days_behind == 1:
                    st.info("数据落后 1 天（可能是非交易日）")
                else:
                    st.warning(f"数据落后 {days_behind} 天")
            except Exception:
                pass
        else:
            st.info("暂无数据新鲜度信息")


if __name__ == "__main__":
    main()
