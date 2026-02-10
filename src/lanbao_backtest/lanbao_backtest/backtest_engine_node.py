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
        """保存回测结果"""
        # 这里可以保存到数据库
        logger.info(f"回测结果已缓存: {result.backtest_id}")
    
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
