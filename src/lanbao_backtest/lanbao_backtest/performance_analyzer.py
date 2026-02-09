"""
绩效分析器
提供详细的回测绩效分析
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class PerformanceAnalyzer:
    """
    绩效分析器
    
    功能:
    - 绩效指标计算
    - 可视化报告生成
    - 归因分析
    """
    
    def __init__(self):
        self._metrics_cache = {}
    
    def analyze(self, result) -> Dict:
        """
        分析回测结果
        
        Args:
            result: 回测结果对象
            
        Returns:
            分析结果字典
        """
        analysis = {
            'summary': self._generate_summary(result),
            'returns': self._analyze_returns(result),
            'risk': self._analyze_risk(result),
            'trades': self._analyze_trades(result),
            'drawdowns': self._analyze_drawdowns(result)
        }
        
        return analysis
    
    def _generate_summary(self, result) -> Dict:
        """生成摘要"""
        return {
            'strategy_id': result.strategy_id,
            'symbol': result.symbol,
            'period': f"{result.start_date} ~ {result.end_date}",
            'total_return': f"{result.total_return:.2%}",
            'annual_return': f"{result.annual_return:.2%}",
            'sharpe_ratio': f"{result.sharpe_ratio:.2f}",
            'max_drawdown': f"{result.max_drawdown:.2%}",
            'win_rate': f"{result.win_rate:.2%}",
            'total_trades': result.total_trades
        }
    
    def _analyze_returns(self, result) -> Dict:
        """分析收益"""
        equity = result.equity_curve
        daily_returns = result.daily_returns
        
        return {
            'total_return': result.total_return,
            'annual_return': result.annual_return,
            'monthly_returns': self._calculate_monthly_returns(equity),
            'best_day': daily_returns.max() if len(daily_returns) > 0 else 0,
            'worst_day': daily_returns.min() if len(daily_returns) > 0 else 0,
            'avg_daily_return': daily_returns.mean() if len(daily_returns) > 0 else 0,
            'positive_days': (daily_returns > 0).sum() if len(daily_returns) > 0 else 0,
            'negative_days': (daily_returns < 0).sum() if len(daily_returns) > 0 else 0
        }
    
    def _analyze_risk(self, result) -> Dict:
        """分析风险"""
        daily_returns = result.daily_returns
        
        if len(daily_returns) == 0:
            return {}
        
        # VaR计算 (95%置信度)
        var_95 = np.percentile(daily_returns, 5)
        
        # CVaR计算
        cvar_95 = daily_returns[daily_returns <= var_95].mean()
        
        return {
            'volatility': result.volatility,
            'max_drawdown': result.max_drawdown,
            'sharpe_ratio': result.sharpe_ratio,
            'sortino_ratio': result.sortino_ratio,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'calmar_ratio': result.annual_return / abs(result.max_drawdown) if result.max_drawdown != 0 else 0
        }
    
    def _analyze_trades(self, result) -> Dict:
        """分析交易"""
        trades = result.trades
        
        if not trades:
            return {}
        
        sell_trades = [t for t in trades if t.action == 'SELL']
        
        if not sell_trades:
            return {}
        
        profits = [t.pnl for t in sell_trades if t.pnl > 0]
        losses = [t.pnl for t in sell_trades if t.pnl <= 0]
        
        return {
            'total_trades': len(trades),
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'win_rate': result.win_rate,
            'avg_profit': np.mean(profits) if profits else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'largest_profit': max(profits) if profits else 0,
            'largest_loss': min(losses) if losses else 0,
            'profit_factor': result.profit_factor
        }
    
    def _analyze_drawdowns(self, result) -> Dict:
        """分析回撤"""
        equity = result.equity_curve
        
        if len(equity) == 0:
            return {}
        
        # 计算回撤
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        
        # 找出回撤区间
        is_drawdown = drawdown < 0
        drawdown_periods = []
        
        start = None
        for i, in_dd in enumerate(is_drawdown):
            if in_dd and start is None:
                start = i
            elif not in_dd and start is not None:
                drawdown_periods.append({
                    'start': equity.index[start],
                    'end': equity.index[i],
                    'duration': i - start,
                    'max_drawdown': drawdown.iloc[start:i].min()
                })
                start = None
        
        return {
            'max_drawdown': result.max_drawdown,
            'avg_drawdown': drawdown.mean(),
            'drawdown_periods': drawdown_periods[:5]  # 前5大回撤
        }
    
    def _calculate_monthly_returns(self, equity: pd.Series) -> pd.Series:
        """计算月度收益"""
        if len(equity) == 0:
            return pd.Series()
        
        # 确保索引是 DatetimeIndex
        if not isinstance(equity.index, pd.DatetimeIndex):
            equity = equity.copy()
            equity.index = pd.to_datetime(equity.index)
        
        # 按月重采样 (ME = Month End)
        monthly = equity.resample('ME').last()
        monthly_returns = monthly.pct_change().dropna()
        
        return monthly_returns
    
    def generate_report_html(self, result) -> str:
        """
        生成HTML报告
        
        Args:
            result: 回测结果
            
        Returns:
            HTML字符串
        """
        analysis = self.analyze(result)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>回测报告 - {result.strategy_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #4CAF50; color: white; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>回测报告</h1>
            
            <div class="summary">
                <h2>基本信息</h2>
                <table>
                    <tr><th>指标</th><th>数值</th></tr>
                    <tr><td>策略ID</td><td>{result.strategy_id}</td></tr>
                    <tr><td>标的</td><td>{result.symbol}</td></tr>
                    <tr><td>回测周期</td><td>{analysis['summary']['period']}</td></tr>
                </table>
            </div>
            
            <h2>收益指标</h2>
            <table>
                <tr><th>指标</th><th>数值</th></tr>
                <tr><td>总收益率</td><td class="{'positive' if result.total_return > 0 else 'negative'}">{analysis['summary']['total_return']}</td></tr>
                <tr><td>年化收益率</td><td>{analysis['summary']['annual_return']}</td></tr>
                <tr><td>夏普比率</td><td>{analysis['summary']['sharpe_ratio']}</td></tr>
            </table>
            
            <h2>风险指标</h2>
            <table>
                <tr><th>指标</th><th>数值</th></tr>
                <tr><td>最大回撤</td><td class="negative">{analysis['summary']['max_drawdown']}</td></tr>
                <tr><td>波动率</td><td>{analysis['risk']['volatility']:.2%}</td></tr>
            </table>
            
            <h2>交易统计</h2>
            <table>
                <tr><th>指标</th><th>数值</th></tr>
                <tr><td>总交易次数</td><td>{result.total_trades}</td></tr>
                <tr><td>胜率</td><td>{analysis['summary']['win_rate']}</td></tr>
                <tr><td>盈亏比</td><td>{result.profit_factor:.2f}</td></tr>
            </table>
        </body>
        </html>
        """
        
        return html
    
    def plot_equity_curve(self, result) -> go.Figure:
        """
        绘制权益曲线
        
        Args:
            result: 回测结果
            
        Returns:
            Plotly图表
        """
        equity = result.equity_curve
        
        fig = go.Figure()
        
        # 权益曲线
        fig.add_trace(go.Scatter(
            x=equity.index,
            y=equity.values,
            mode='lines',
            name='权益曲线',
            line=dict(color='blue')
        ))
        
        # 初始资金线
        fig.add_hline(y=self._config.initial_capital if hasattr(self, '_config') else 100000, 
                      line_dash="dash", line_color="gray", name="初始资金")
        
        fig.update_layout(
            title=f'权益曲线 - {result.strategy_id}',
            xaxis_title='日期',
            yaxis_title='资金',
            hovermode='x unified'
        )
        
        return fig
