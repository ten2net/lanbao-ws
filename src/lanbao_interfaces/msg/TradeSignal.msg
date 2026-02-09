# 交易信号消息
std_msgs/Header header
string symbol          # 股票代码
string action          # 动作: BUY, SELL
int32 quantity         # 数量
float64 price          # 目标价格
string order_type      # 订单类型: MARKET, LIMIT
string strategy_id     # 策略ID
float64 risk_level     # 风险等级
int64 timestamp        # 时间戳
