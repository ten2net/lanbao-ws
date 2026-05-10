export interface BacktestListItem {
  backtest_id: string;
  strategy_name: string;
  strategy_id: string;
  symbol: string;
  start_date: string;
  end_date: string;
  total_return: number | null;
  annual_return: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  win_rate: number | null;
  trade_count: number | null;
  tags: string[];
  status: string;
  created_at: string | null;
}

export interface BacktestListResponse {
  total: number;
  page: number;
  limit: number;
  items: BacktestListItem[];
}

export interface BacktestDetail {
  backtest_id: string;
  meta: Record<string, any>;
  performance: Record<string, any>;
  files: Record<string, string>;
}

export interface Trade {
  trade_id: string;
  trade_date: string;
  action: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  amount: number;
  commission: number;
  pnl: number | null;
}

export interface EquityPoint {
  date: string;
  equity: number;
  drawdown_pct: number;
  daily_return_pct: number;
}

export interface MonthlyMatrix {
  [year: string]: { [month: string]: number };
}

export interface StrategyTemplate {
  strategy_id: string;
  name: string;
  description: string;
  default_params: Record<string, any>;
}

export interface RunBacktestRequest {
  strategy_id: string;
  symbol: string;
  start_date: string;
  end_date: string;
  params: Record<string, any>;
}

export interface BacktestFilters {
  strategy?: string;
  symbol?: string;
  tags: string[];
  dateRange?: [string, string];
}
