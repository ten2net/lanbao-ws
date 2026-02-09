# 订单状态消息
std_msgs/Header header
string order_id        # 订单ID
string symbol          # 股票代码
string status          # 状态: PENDING, FILLED, PARTIAL, CANCELLED, REJECTED
int32 filled_qty       # 成交数量
float64 filled_price   # 成交价格
float64 total_amount   # 总金额
string message         # 状态信息
int64 timestamp        # 时间戳
