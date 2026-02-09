# 回测结果消息
std_msgs/Header header
string backtest_id     # 回测ID
string strategy_id     # 策略ID
string symbol          # 股票代码
string start_date      # 开始日期
string end_date        # 结束日期

# 绩效指标
float64 total_return       # 总收益率
float64 annual_return      # 年化收益率
float64 sharpe_ratio       # 夏普比率
float64 max_drawdown       # 最大回撤
float64 volatility         # 波动率
float64 win_rate           # 胜率
float64 profit_factor      # 盈亏比
int32 total_trades         # 总交易次数
float64 avg_trade_return   # 平均交易收益

string status          # 状态: RUNNING, COMPLETED, FAILED
string message         # 状态信息
int64 timestamp        # 时间戳
