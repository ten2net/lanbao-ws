# 市场评估消息
std_msgs/Header header
string market_type     # 市场类型: BULL, BEAR, OSCILLATING
float64 sentiment      # 市场情绪 0.0-1.0
float64 trend_strength # 趋势强度
string[] hot_sectors   # 热门板块
string[] cold_sectors  # 冷门板块
float64 volatility_index  # 波动率指数
int64 timestamp        # 时间戳
