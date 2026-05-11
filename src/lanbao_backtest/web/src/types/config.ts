export interface BacktestConfig {
  default_initial_capital: number;
  default_commission_rate: number;
  default_slippage: number;
  default_backtest_days: number;
}

export interface RiskConfig {
  max_single_loss_pct: number;
  max_drawdown_threshold: number;
  max_position_pct: number;
  circuit_breaker_enabled: boolean;
}

export interface DataSyncConfig {
  auto_sync_enabled: boolean;
  sync_time: string;
  source_priority: string;
}

export interface NotificationConfig {
  webhook_url: string | null;
  alert_level_threshold: string;
}

export interface SystemConfig {
  backtest: BacktestConfig;
  risk: RiskConfig;
  data_sync: DataSyncConfig;
  notification: NotificationConfig;
}
