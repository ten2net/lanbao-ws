# 数据同步状态详情
string status           # 状态: idle / running / completed / failed
string last_sync_time   # 上次同步时间
int32 total_symbols     # 总股票数
int32 success_count     # 成功数
int32 failed_count      # 失败数
float64 duration_seconds # 耗时(秒)
string message          # 消息
