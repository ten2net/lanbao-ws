# 股票信号消息
std_msgs/Header header
string symbol          # 股票代码
string signal_type     # 信号类型: BUY, SELL, HOLD
float64 strength       # 信号强度 0.0-1.0
string strategy_id     # 策略ID
string reason          # 信号原因
int64 timestamp        # 时间戳
