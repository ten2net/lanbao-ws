"""
回测引擎ROS2节点
"""
import rclpy
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger
import uuid

from lanbao_core import LanBaoBaseNode, NodeConfig
from lanbao_interfaces.msg import BacktestResult as BacktestResultMsg
from lanbao_interfaces.srv import RunBacktest, GetMarketData
from lanbao_interfaces.action import BacktestStrategy
from rclpy.action import ActionServer

from .backtest_engine import BacktestEngine, BacktestConfig
from .performance_analyzer import PerformanceAnalyzer


class BacktestEngineNode(LanBaoBaseNode):
    """
    回测引擎节点
    
    职责:
    - 接收回测请求
    - 执行向量化回测
    - 返回回测结果
    """
    
    def __init__(self):
        config = NodeConfig(
            node_name='backtest_engine_node',
            node_type='backtest_engine',
            publish_rate=0.1
        )
        super().__init__('backtest_engine_node', config)
        
        # 回测引擎
        self._engine = BacktestEngine(BacktestConfig())
        self._analyzer = PerformanceAnalyzer()
        
        # 市场数据客户端
        self._market_data_client = None
        
    def initialize(self) -> bool:
        """初始化节点"""
        try:
            # 创建市场数据服务客户端
            self._market_data_client = self.create_client(
                GetMarketData,
                'market_data/get'
            )
            
            # 等待服务可用
            if not self._market_data_client.wait_for_service(timeout_sec=5.0):
                logger.warning("市场数据服务未就绪，将尝试重新连接")
            
            # 设置服务
            self._setup_services()
            
            # 设置动作服务器
            self._setup_action_server()
            
            logger.info("回测引擎节点初始化完成")
            return True
            
        except Exception as e:
            logger.exception(f"回测引擎节点初始化失败: {e}")
            return False
    
    def _setup_services(self):
        """设置ROS2服务"""
        # 运行回测服务
        self._backtest_service = self.create_service(
            RunBacktest,
            'backtest/run',
            self._handle_run_backtest,
            callback_group=self._callback_group
        )
        
        logger.info("回测服务已设置")
    
    def _setup_action_server(self):
        """设置动作服务器"""
        self._action_server = ActionServer(
            self,
            BacktestStrategy,
            'backtest/strategy',
            self._execute_backtest_action,
            callback_group=self._callback_group
        )
        
        logger.info("回测动作服务器已设置")
    
    def _handle_run_backtest(self, request, response):
        """
        处理回测请求
        """
        try:
            logger.info(f"收到回测请求: {request.strategy_id} for {request.symbol}")
            
            # 获取市场数据
            data = self._fetch_market_data(
                request.symbol,
                request.start_date,
                request.end_date
            )
            
            if data is None or data.empty:
                response.success = False
                response.message = f"无法获取 {request.symbol} 的市场数据"
                return response
            
            # 生成回测ID
            # 清理策略ID中的特殊字符
            clean_strategy_id = request.strategy_id.replace('/', '_').replace('\\', '_')
            backtest_id = f"bt_{clean_strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 获取策略信号生成器
            signal_generator = self._get_signal_generator(request.strategy_id)
            
            # 执行回测
            result = self._engine.run_backtest(
                strategy_id=request.strategy_id,
                symbol=request.symbol,
                data=data,
                signal_generator=signal_generator,
                backtest_id=backtest_id
            )
            
            # 保存到数据库
            self._save_backtest_result(result)
            
            response.success = True
            response.backtest_id = backtest_id
            response.message = f"回测完成，总收益: {result.total_return:.2%}"
            
            # 发布回测结果
            self._publish_result(result)
            
            logger.info(f"回测完成: {backtest_id}, 收益: {result.total_return:.2%}")
            
        except Exception as e:
            logger.exception(f"回测执行失败: {e}")
            response.success = False
            response.message = f"回测失败: {str(e)}"
        
        return response
    
    def _execute_backtest_action(self, goal_handle):
        """
        执行回测动作
        """
        goal = goal_handle.request
        # 清理策略ID中的特殊字符
        clean_strategy_id = goal.strategy_id.replace('/', '_').replace('\\', '_')
        backtest_id = f"bt_{clean_strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"开始动作回测: {backtest_id}")
        
        feedback_msg = BacktestStrategy.Feedback()
        result_msg = BacktestStrategy.Result()
        
        try:
            # 发布进度
            feedback_msg.status = "获取市场数据"
            feedback_msg.progress = 0.1
            goal_handle.publish_feedback(feedback_msg)
            
            # 获取数据
            data = self._fetch_market_data(goal.symbol, goal.start_date, goal.end_date)
            
            if data is None or data.empty:
                result_msg.success = False
                result_msg.message = "无法获取市场数据"
                goal_handle.succeed()
                return result_msg
            
            # 发布进度
            feedback_msg.status = "执行回测计算"
            feedback_msg.progress = 0.5
            goal_handle.publish_feedback(feedback_msg)
            
            # 执行回测
            signal_generator = self._get_signal_generator(goal.strategy_id)
            result = self._engine.run_backtest(
                strategy_id=goal.strategy_id,
                symbol=goal.symbol,
                data=data,
                signal_generator=signal_generator,
                backtest_id=backtest_id
            )
            
            # 发布进度
            feedback_msg.status = "计算绩效指标"
            feedback_msg.progress = 0.8
            goal_handle.publish_feedback(feedback_msg)
            
            # 保存结果
            self._save_backtest_result(result)
            
            # 构建结果消息
            result_msg.success = True
            result_msg.result.backtest_id = backtest_id
            result_msg.result.strategy_id = goal.strategy_id
            result_msg.result.symbol = goal.symbol
            result_msg.result.start_date = goal.start_date
            result_msg.result.end_date = goal.end_date
            result_msg.result.total_return = result.total_return
            result_msg.result.annual_return = result.annual_return
            result_msg.result.sharpe_ratio = result.sharpe_ratio
            result_msg.result.max_drawdown = result.max_drawdown
            result_msg.result.volatility = result.volatility
            result_msg.result.win_rate = result.win_rate
            result_msg.result.total_trades = result.total_trades
            result_msg.result.status = "COMPLETED"
            result_msg.message = f"回测完成，总收益: {result.total_return:.2%}"
            
            goal_handle.succeed()
            
            # 发布结果
            self._publish_result(result)
            
        except Exception as e:
            logger.exception(f"动作回测失败: {e}")
            result_msg.success = False
            result_msg.message = f"回测失败: {str(e)}"
            goal_handle.abort()
        
        return result_msg
    
    def _fetch_market_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取市场数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame包含市场数据
        """
        try:
            if self._market_data_client and self._market_data_client.service_is_ready():
                request = GetMarketData.Request()
                request.symbol = symbol
                request.start_date = start_date
                request.end_date = end_date
                
                future = self._market_data_client.call_async(request)
                rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)
                
                if future.done():
                    response = future.result()
                    if response.success:
                        # 转换为DataFrame
                        data = []
                        for msg in response.data:
                            data.append({
                                'date': pd.to_datetime(msg.timestamp, unit='ms'),
                                'open': msg.open,
                                'high': msg.high,
                                'low': msg.low,
                                'close': msg.close,
                                'volume': msg.volume,
                                'amount': msg.amount
                            })
                        return pd.DataFrame(data).set_index('date')
            
            logger.warning("市场数据服务不可用，回测无法执行")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return pd.DataFrame()
    
    def _get_signal_generator(self, strategy_id: str):
        """
        获取策略信号生成器
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            信号生成函数
        """
        # 基础策略信号生成器 - 双均线交叉
        def ma_cross_signal(data: pd.DataFrame) -> pd.Series:
            """双均线交叉策略"""
            df = data.copy()
            df['ma5'] = df['close'].rolling(5).mean()
            df['ma20'] = df['close'].rolling(20).mean()
            
            signal = pd.Series(0, index=df.index)
            signal[df['ma5'] > df['ma20']] = 1  # 金叉买入
            signal[df['ma5'] < df['ma20']] = -1  # 死叉卖出
            
            return signal
        
        # 根据策略ID返回不同的生成器
        if strategy_id == 'ma_cross':
            return ma_cross_signal
        elif strategy_id == 'rsi':
            def rsi_signal(data: pd.DataFrame) -> pd.Series:
                """RSI策略"""
                df = data.copy()
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                
                signal = pd.Series(0, index=df.index)
                signal[rsi < 30] = 1  # 超卖买入
                signal[rsi > 70] = -1  # 超买卖出
                
                return signal
            return rsi_signal
        else:
            return ma_cross_signal
    
    def _save_backtest_result(self, result):
        """保存回测结果到 v2.0 JSON 文件"""
        import json
        import os

        project_root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ))
        default_dir = os.path.join(project_root, "reports")
        reports_dir = os.environ.get("LANBAO_REPORTS_DIR", default_dir)
        reports_dir = os.path.expanduser(reports_dir)
        os.makedirs(reports_dir, exist_ok=True)

        backtest_id = result.backtest_id

        # 1) 主文件
        try:
            perf = self._calculate_v2_performance(result)

            main_data = {
                "schema_version": "2.0",
                "backtest_id": backtest_id,
                "meta": {
                    "strategy_id": result.strategy_id,
                    "strategy_name": result.strategy_id,
                    "strategy_params": {},
                    "symbol": result.symbol,
                    "start_date": result.start_date,
                    "end_date": result.end_date,
                    "total_trading_days": len(result.equity_curve),
                    "created_at": datetime.now().isoformat(),
                    "duration_seconds": 0,
                    "status": "completed",
                    "tags": [],
                },
                "performance": perf,
                "files": {
                    "equity": f"{backtest_id}.equity.json",
                    "trades": f"{backtest_id}.trades.json",
                    "monthly": f"{backtest_id}.monthly.json",
                },
            }

            with open(os.path.join(reports_dir, f"{backtest_id}.json"), "w", encoding="utf-8") as f:
                json.dump(main_data, f, ensure_ascii=False, indent=2)
            logger.info(f"回测主文件已保存: {backtest_id}.json")

        except Exception as e:
            logger.error(f"保存回测主文件失败: {e}")

        # 2) 权益曲线
        try:
            equity_data = {"backtest_id": backtest_id, "series": []}
            if len(result.equity_curve) > 0:
                cummax = result.equity_curve.cummax()
                drawdown = (result.equity_curve - cummax) / cummax
                daily_returns = result.equity_curve.pct_change().fillna(0)

                for date, equity in result.equity_curve.items():
                    date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)
                    dd = drawdown.get(date, 0)
                    dr = daily_returns.get(date, 0)
                    equity_data["series"].append({
                        "date": date_str,
                        "equity": round(float(equity), 2),
                        "drawdown_pct": round(float(dd) * 100, 2),
                        "daily_return_pct": round(float(dr) * 100, 2),
                    })

            with open(os.path.join(reports_dir, f"{backtest_id}.equity.json"), "w", encoding="utf-8") as f:
                json.dump(equity_data, f, ensure_ascii=False, indent=2)
            logger.info(f"权益曲线已保存: {backtest_id}.equity.json")

        except Exception as e:
            logger.error(f"保存权益曲线失败: {e}")

        # 3) 交易明细
        try:
            trades_data = {"backtest_id": backtest_id, "trades": []}
            for t in result.trades:
                trades_data["trades"].append({
                    "trade_id": t.trade_id,
                    "trade_date": t.trade_date.strftime("%Y-%m-%d") if hasattr(t.trade_date, "strftime") else str(t.trade_date),
                    "action": t.action,
                    "quantity": t.quantity,
                    "price": round(t.price, 4),
                    "amount": round(t.amount, 2),
                    "commission": round(t.commission, 4),
                    "pnl": round(t.pnl, 2) if t.pnl else None,
                })

            with open(os.path.join(reports_dir, f"{backtest_id}.trades.json"), "w", encoding="utf-8") as f:
                json.dump(trades_data, f, ensure_ascii=False, indent=2)
            logger.info(f"交易明细已保存: {backtest_id}.trades.json")

        except Exception as e:
            logger.error(f"保存交易明细失败: {e}")

        # 4) 月度收益
        try:
            monthly_data = {"backtest_id": backtest_id, "matrix": {}}
            if len(result.equity_curve) > 0:
                monthly = result.equity_curve.resample('ME').last().pct_change().dropna()
                for date, value in monthly.items():
                    year = str(date.year)
                    month = f"{date.month:02d}"
                    if year not in monthly_data["matrix"]:
                        monthly_data["matrix"][year] = {}
                    monthly_data["matrix"][year][month] = round(float(value) * 100, 2)

            with open(os.path.join(reports_dir, f"{backtest_id}.monthly.json"), "w", encoding="utf-8") as f:
                json.dump(monthly_data, f, ensure_ascii=False, indent=2)
            logger.info(f"月度收益已保存: {backtest_id}.monthly.json")

        except Exception as e:
            logger.error(f"保存月度收益失败: {e}")

    def _calculate_v2_performance(self, result):
        """计算 v2.0 绩效指标"""
        equity = result.equity_curve
        initial_capital = self._config.initial_capital
        daily_returns = equity.pct_change().dropna()

        total_return = (equity.iloc[-1] - initial_capital) / initial_capital if len(equity) > 0 else 0
        days = len(equity)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 1 else 0
        volatility = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 0 else 0
        sharpe = (annual_return - 0.03) / volatility if volatility > 0 else 0

        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        max_dd = drawdown.min()

        in_drawdown = drawdown < 0
        max_dd_duration = 0
        current_duration = 0
        for v in in_drawdown:
            if v:
                current_duration += 1
                max_dd_duration = max(max_dd_duration, current_duration)
            else:
                current_duration = 0

        sell_trades = [t for t in result.trades if t.action == "SELL"]
        wins = sum(1 for t in sell_trades if t.pnl > 0)
        losses = sum(1 for t in sell_trades if t.pnl <= 0)
        win_rate = wins / len(sell_trades) if sell_trades else 0
        profit_factor = 0
        if sell_trades:
            gross_profit = sum(t.pnl for t in sell_trades if t.pnl > 0)
            gross_loss = abs(sum(t.pnl for t in sell_trades if t.pnl < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        holding_days = []
        buy_date = None
        for t in result.trades:
            if t.action == "BUY":
                buy_date = t.trade_date
            elif t.action == "SELL" and buy_date:
                if hasattr(t.trade_date, "__sub__"):
                    holding_days.append((t.trade_date - buy_date).days)
                buy_date = None
        avg_holding = np.mean(holding_days) if holding_days else 0

        return {
            "returns": {
                "total_return_pct": round(total_return * 100, 2),
                "annual_return_pct": round(annual_return * 100, 2),
                "daily_return_mean_pct": round(daily_returns.mean() * 100, 2) if len(daily_returns) > 0 else 0,
                "daily_return_std_pct": round(daily_returns.std() * 100, 2) if len(daily_returns) > 0 else 0,
                "best_day_pct": round(daily_returns.max() * 100, 2) if len(daily_returns) > 0 else 0,
                "worst_day_pct": round(daily_returns.min() * 100, 2) if len(daily_returns) > 0 else 0,
                "positive_days": int((daily_returns > 0).sum()),
                "negative_days": int((daily_returns < 0).sum()),
            },
            "risk": {
                "sharpe_ratio": round(sharpe, 2),
                "sortino_ratio": round(sharpe, 2),
                "max_drawdown_pct": round(max_dd * 100, 2),
                "max_drawdown_duration_days": max_dd_duration,
                "volatility_annual_pct": round(volatility * 100, 2),
                "var_95_pct": round(np.percentile(daily_returns, 5) * 100, 2) if len(daily_returns) > 0 else 0,
                "calmar_ratio": round(annual_return / abs(max_dd), 2) if max_dd != 0 else 0,
            },
            "trades": {
                "total_count": len(result.trades),
                "winning_count": wins,
                "losing_count": losses,
                "win_rate_pct": round(win_rate * 100, 2),
                "profit_factor": round(profit_factor, 2),
                "avg_trade_return_pct": round(np.mean([t.pnl for t in sell_trades]) / initial_capital * 100, 2) if sell_trades else 0,
                "avg_win_pct": round(np.mean([t.pnl for t in sell_trades if t.pnl > 0]) / initial_capital * 100, 2) if any(t.pnl > 0 for t in sell_trades) else 0,
                "avg_loss_pct": round(np.mean([t.pnl for t in sell_trades if t.pnl <= 0]) / initial_capital * 100, 2) if any(t.pnl <= 0 for t in sell_trades) else 0,
                "largest_win_pct": round(max((t.pnl for t in sell_trades if t.pnl > 0), default=0) / initial_capital * 100, 2),
                "largest_loss_pct": round(min((t.pnl for t in sell_trades if t.pnl <= 0), default=0) / initial_capital * 100, 2),
                "avg_holding_days": round(avg_holding, 1),
            },
        }
    
    def _publish_result(self, result):
        """发布回测结果"""
        try:
            msg = BacktestResultMsg()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.backtest_id = result.backtest_id
            msg.strategy_id = result.strategy_id
            msg.symbol = result.symbol
            msg.start_date = result.start_date
            msg.end_date = result.end_date
            msg.total_return = result.total_return
            msg.annual_return = result.annual_return
            msg.sharpe_ratio = result.sharpe_ratio
            msg.max_drawdown = result.max_drawdown
            msg.volatility = result.volatility
            msg.win_rate = result.win_rate
            msg.total_trades = result.total_trades
            msg.status = "COMPLETED"
            msg.timestamp = int(datetime.now().timestamp() * 1000)
            
            # 发布结果
            # self._result_publisher.publish(msg)
            
        except Exception as e:
            logger.error(f"发布回测结果失败: {e}")
    
    def start(self) -> bool:
        """启动节点"""
        logger.info("回测引擎节点启动完成")
        return True
    
    def stop(self):
        """停止节点"""
        logger.info("回测引擎节点已停止")


def main(args=None):
    """节点入口函数"""
    rclpy.init(args=args)
    
    node = BacktestEngineNode()
    
    try:
        node.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        node.shutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
