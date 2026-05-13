# 投研报告完成通知
std_msgs/Header header
string report_id
string report_type          # "market_daily" | "stock_analysis"
string[] symbols
string summary              # 一句话摘要
string verdict              # STRONG_BUY | BUY | HOLD | SELL | STRONG_SELL
float32 confidence          # 0.0-1.0
string created_at
