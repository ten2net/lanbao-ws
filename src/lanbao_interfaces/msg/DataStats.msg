# DuckDB 数据概况统计
int64 total_records      # 总记录数
int32 total_symbols      # 覆盖股票数
string start_date        # 起始日期 (YYYY-MM-DD)
string end_date          # 结束日期 (YYYY-MM-DD)
float64 db_size_mb       # 数据库文件大小 (MB)
string[] exchange_names  # 交易所名称列表
int32[] exchange_counts  # 各交易所股票数量
