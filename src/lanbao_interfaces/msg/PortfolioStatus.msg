# 持仓状态消息
std_msgs/Header header
string account_id      # 账户ID
float64 total_value    # 总市值
float64 cash           # 现金
float64 market_value   # 市值
float64 day_pnl        # 当日盈亏
float64 total_pnl      # 总盈亏
float64 drawdown       # 回撤
StockPosition[] positions  # 持仓列表
