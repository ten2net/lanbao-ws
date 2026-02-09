"""
揽宝回测引擎 - 向量化回测实现
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003  # 佣金率
    slippage: float = 0.001  # 滑点
    position_size: float = 0.1  # 仓位比例
    stop_loss: float = 0.05  # 止损比例
    take_profit: float = 0.1  # 止盈比例


@dataclass
class Trade:
    """交易记录"""
    trade_id: str
    symbol: str
    trade_date: datetime
    action: str  # BUY, SELL
    quantity: int
    price: float
    amount: float
    commission: float
    pnl: float = 0.0


@dataclass
class BacktestResult:
    """回测结果"""
    backtest_id: str
    strategy_id: str
    symbol: str
    start_date: str
    end_date: str
    
    # 收益指标
    total_return: float = 0.0
    annual_return: float = 0.0
    total_pnl: float = 0.0
    
    # 风险指标
    max_drawdown: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    # 交易统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_trade_return: float = 0.0
    profit_factor: float = 0.0
    
    # 数据
    equity_curve: pd.Series = field(default_factory=pd.Series)
    trades: List[Trade] = field(default_factory=list)
    daily_returns: pd.Series = field(default_factory=pd.Series)


class BacktestEngine:
    """
    回测引擎
    
    功能:
    - 向量化回测计算
    - 交易成本模拟
    - 绩效分析
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置
        """
        self._config = config or BacktestConfig()
        self._results: Dict[str, BacktestResult] = {}
        
    def run_backtest(self, strategy_id: str, symbol: str, 
                     data: pd.DataFrame, 
                     signal_generator: Callable[[pd.DataFrame], pd.Series],
                     backtest_id: Optional[str] = None) -> BacktestResult:
        """
        运行回测
        
        Args:
            strategy_id: 策略ID
            symbol: 股票代码
            data: 历史数据DataFrame (OHLCV)
            signal_generator: 信号生成函数，返回-1(卖), 0(持有), 1(买)
            backtest_id: 回测ID，不指定则自动生成
            
        Returns:
            回测结果
        """
        if backtest_id is None:
            backtest_id = f"bt_{strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"开始回测: {backtest_id} for {symbol}")
        
        # 数据准备
        df = data.copy()
        df = df.sort_index()
        
        # 生成交易信号
        signals = signal_generator(df)
        
        # 执行回测
        result = self._execute_backtest(
            backtest_id, strategy_id, symbol, df, signals
        )
        
        # 计算绩效指标
        result = self._calculate_metrics(result)
        
        # 保存结果
        self._results[backtest_id] = result
        
        logger.info(f"回测完成: {backtest_id}, 总收益: {result.total_return:.2%}")
        
        return result
    
    def _execute_backtest(self, backtest_id: str, strategy_id: str, 
                          symbol: str, data: pd.DataFrame, 
                          signals: pd.Series) -> BacktestResult:
        """
        执行回测计算
        
        Args:
            backtest_id: 回测ID
            strategy_id: 策略ID
            symbol: 股票代码
            data: 历史数据
            signals: 交易信号
            
        Returns:
            回测结果
        """
        config = self._config
        
        # 初始化
        capital = config.initial_capital
        position = 0  # 持仓数量
        trades = []
        equity = [capital]
        
        # 向量化计算仓位
        # 这里使用简化的事件驱动逻辑
        for i in range(1, len(data)):
            date = data.index[i]
            price = data['close'].iloc[i]
            prev_price = data['close'].iloc[i-1]
            signal = signals.iloc[i-1]  # 使用前一天的信号
            
            # 交易逻辑
            if signal == 1 and position == 0:  # 买入
                # 计算买入数量
                trade_capital = capital * config.position_size
                quantity = int(trade_capital / price)
                
                if quantity > 0:
                    amount = quantity * price
                    commission = amount * config.commission_rate
                    slippage_cost = amount * config.slippage
                    
                    total_cost = amount + commission + slippage_cost
                    
                    if total_cost <= capital:
                        position = quantity
                        capital -= total_cost
                        
                        trades.append(Trade(
                            trade_id=f"{backtest_id}_{len(trades)}",
                            symbol=symbol,
                            trade_date=date,
                            action='BUY',
                            quantity=quantity,
                            price=price,
                            amount=amount,
                            commission=commission + slippage_cost
                        ))
            
            elif signal == -1 and position > 0:  # 卖出
                amount = position * price
                commission = amount * config.commission_rate
                slippage_cost = amount * config.slippage
                
                total_cost = commission + slippage_cost
                
                # 计算盈亏
                avg_buy_price = trades[-1].price if trades else price
                pnl = (price - avg_buy_price) * position - total_cost
                
                capital += amount - total_cost
                
                trades.append(Trade(
                    trade_id=f"{backtest_id}_{len(trades)}",
                    symbol=symbol,
                    trade_date=date,
                    action='SELL',
                    quantity=position,
                    price=price,
                    amount=amount,
                    commission=total_cost,
                    pnl=pnl
                ))
                
                position = 0
            
            # 计算当前权益
            current_equity = capital + position * price
            equity.append(current_equity)
        
        # 最后一个交易日平仓
        if position > 0:
            final_price = data['close'].iloc[-1]
            amount = position * final_price
            trades[-1].pnl = amount - trades[-1].amount if trades else 0
            capital += amount
            equity[-1] = capital
        
        # 构建结果
        result = BacktestResult(
            backtest_id=backtest_id,
            strategy_id=strategy_id,
            symbol=symbol,
            start_date=str(data.index[0]),
            end_date=str(data.index[-1]),
            total_pnl=capital - config.initial_capital,
            equity_curve=pd.Series(equity, index=data.index),
            trades=trades
        )
        
        return result
    
    def _calculate_metrics(self, result: BacktestResult) -> BacktestResult:
        """
        计算绩效指标
        
        Args:
            result: 回测结果
            
        Returns:
            添加了指标的回测结果
        """
        equity = result.equity_curve
        initial_capital = self._config.initial_capital
        
        # 总收益
        result.total_return = (equity.iloc[-1] - initial_capital) / initial_capital
        
        # 年化收益
        days = len(equity)
        if days > 1:
            result.annual_return = (1 + result.total_return) ** (252 / days) - 1
        
        # 日收益率
        daily_returns = equity.pct_change().dropna()
        result.daily_returns = daily_returns
        
        # 波动率
        result.volatility = daily_returns.std() * np.sqrt(252)
        
        # 夏普比率 (假设无风险利率为3%)
        risk_free_rate = 0.03
        if result.volatility > 0:
            result.sharpe_ratio = (result.annual_return - risk_free_rate) / result.volatility
        
        # 最大回撤
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        result.max_drawdown = drawdown.min()
        
        # 交易统计
        trades = result.trades
        result.total_trades = len(trades)
        
        if trades:
            sell_trades = [t for t in trades if t.action == 'SELL']
            if sell_trades:
                result.winning_trades = sum(1 for t in sell_trades if t.pnl > 0)
                result.losing_trades = sum(1 for t in sell_trades if t.pnl <= 0)
                result.win_rate = result.winning_trades / len(sell_trades)
                result.avg_trade_return = np.mean([t.pnl for t in sell_trades])
                
                # 盈亏比
                gross_profit = sum(t.pnl for t in sell_trades if t.pnl > 0)
                gross_loss = abs(sum(t.pnl for t in sell_trades if t.pnl < 0))
                if gross_loss > 0:
                    result.profit_factor = gross_profit / gross_loss
        
        return result
    
    def get_result(self, backtest_id: str) -> Optional[BacktestResult]:
        """获取回测结果"""
        return self._results.get(backtest_id)
    
    def get_all_results(self) -> Dict[str, BacktestResult]:
        """获取所有回测结果"""
        return self._results.copy()
    
    def compare_results(self, backtest_ids: List[str]) -> pd.DataFrame:
        """
        比较多个回测结果
        
        Args:
            backtest_ids: 回测ID列表
            
        Returns:
            比较结果DataFrame
        """
        results = []
        for bid in backtest_ids:
            result = self._results.get(bid)
            if result:
                results.append({
                    'backtest_id': bid,
                    'strategy_id': result.strategy_id,
                    'symbol': result.symbol,
                    'total_return': result.total_return,
                    'annual_return': result.annual_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'win_rate': result.win_rate,
                    'total_trades': result.total_trades
                })
        
        return pd.DataFrame(results)
