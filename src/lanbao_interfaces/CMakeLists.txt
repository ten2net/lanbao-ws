cmake_minimum_required(VERSION 3.8)
project(lanbao_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  # 消息定义
  "msg/MarketData.msg"
  "msg/StockSignal.msg"
  "msg/TradeSignal.msg"
  "msg/OrderStatus.msg"
  "msg/StockPosition.msg"
  "msg/PortfolioStatus.msg"
  "msg/RiskAlert.msg"
  "msg/BacktestResult.msg"
  "msg/StrategyStatus.msg"
  "msg/NodeStatus.msg"
  "msg/MarketAssessment.msg"
  "msg/PositionAllocation.msg"
  "msg/SystemAlert.msg"
  "msg/DataStats.msg"
  "msg/DataQualityItem.msg"
  "msg/SyncStatusDetail.msg"
  "msg/SystemMetrics.msg"
  "msg/DataTable.msg"
  "msg/ResearchReport.msg"

  # 服务定义
  "srv/GetMarketData.srv"
  "srv/ExecuteOrder.srv"
  "srv/RunBacktest.srv"
  "srv/ManageStrategy.srv"
  "srv/CheckRisk.srv"
  "srv/GetNodeStatus.srv"
  "srv/GetDataStats.srv"
  "srv/GetDataQuality.srv"
  "srv/GetSyncStatus.srv"
  "srv/GetDataTables.srv"
  "srv/GetTablePreview.srv"
  "srv/GetResearchReport.srv"
  "srv/GetFinancialData.srv"
  "srv/SaveResearchReport.srv"

  # 动作定义
  "action/BacktestStrategy.action"
  "action/DeployStrategy.action"
  "action/CircuitBreaker.action"
  "action/RunResearch.action"
  
  DEPENDENCIES std_msgs builtin_interfaces
)

ament_package()
