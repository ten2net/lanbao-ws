# 市场数据消息
std_msgs/Header header
string symbol          # 股票代码
string exchange        # 交易所
float64 open           # 开盘价
float64 high           # 最高价
float64 low            # 最低价
float64 close          # 收盘价
float64 volume         # 成交量
float64 amount         # 成交额
float64 pre_close      # 昨收价
float64 change_pct     # 涨跌幅
string data_source     # 数据源
int64 timestamp        # 时间戳
