# 仓位分配消息
std_msgs/Header header
string strategy_id     # 策略ID
string symbol          # 股票代码
float64 target_weight  # 目标权重
float64 current_weight # 当前权重
float64 adjustment     # 调整量
string reason          # 调整原因
int64 timestamp        # 时间戳
