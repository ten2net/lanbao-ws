# 节点状态消息
std_msgs/Header header
string node_name       # 节点名称
string node_type       # 节点类型
string status          # 状态: INITIALIZING, RUNNING, SYNCING, ERROR, STOPPED
float64 cpu_usage      # CPU使用率
float64 memory_usage   # 内存使用率
int32 message_count    # 消息计数
string last_error      # 最后错误
int64 timestamp        # 时间戳
