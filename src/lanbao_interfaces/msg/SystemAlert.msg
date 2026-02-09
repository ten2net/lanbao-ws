# 系统告警消息
std_msgs/Header header
string alert_type      # 告警类型: INFO, WARNING, ERROR, CRITICAL
string component       # 组件名称
string message         # 告警内容
string details         # 详细信息
int64 timestamp        # 时间戳
