# 策略状态消息
std_msgs/Header header
string strategy_id     # 策略ID
string strategy_name   # 策略名称
string state           # 状态: DRAFT, VALIDATING, BACKTESTING, SIMULATING, RUNNING, PAUSED, STOPPED
float64 performance    # 策略表现
string[] symbols       # 交易标的
float64 risk_level     # 风险等级
int64 timestamp        # 时间戳
