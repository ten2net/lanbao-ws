export interface DataTableInfo {
  name: string;
  record_count: number;
  date_start?: string;
  date_end?: string;
  last_updated?: string;
  quality_score: number;
}

export interface DataSummary {
  total_symbols: number;
  total_daily_records: number;
  last_sync_time: string | null;
  coverage_days: number;
}

export interface SyncTask {
  id: string;
  source: string;
  status: string;
  progress: number;
  success_count: number;
  failed_count: number;
  duration_seconds: number | null;
}

export interface QualityReport {
  table: string;
  missing_rate: number;
  coverage_score: number;
  overall_score: number;
}

export interface ColumnInfo {
  name: string;
  type: string;
}

export interface TablePreview {
  table: string;
  columns: ColumnInfo[];
  rows: (string | number | null)[][];
  total: number;
  limit: number;
}
