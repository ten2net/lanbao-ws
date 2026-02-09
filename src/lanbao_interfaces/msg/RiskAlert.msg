# 风险告警消息
std_msgs/Header header
string alert_id        # 告警ID
string alert_type      # 告警类型: POSITION, DRAWDOWN, VOLATILITY, SYSTEM
string level           # 等级: LOW, MEDIUM, HIGH, CRITICAL
string message         # 告警内容
float64 current_value  # 当前值
float64 threshold      # 阈值
string[] affected_strategies  # 影响策略
int64 timestamp        # 时间戳
