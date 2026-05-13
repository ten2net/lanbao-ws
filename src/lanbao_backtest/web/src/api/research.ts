import { apiClient } from './client';

export interface TriggerDailyRequest {
  symbols?: string[];
}

export interface TriggerStockRequest {
  symbol: string;
}

export interface ResearchStatus {
  report_id: string;
  status: string;
  progress: number;
  message: string;
  current_agent?: string;
}

export interface ResearchReport {
  report_id: string;
  report_type: string;
  created_at: string;
  summary: {
    market_trend: string;
    overall_verdict: string;
    confidence: number;
    top_sectors: string[];
    risk_level: string;
  };
  stock_analyses: Array<{
    symbol: string;
    name: string;
    synthesis?: {
      verdict: string;
      score: number;
      bull_case: string[];
      bear_case: string[];
      position_suggestion: string;
      risk_notes: string[];
    };
  }>;
}

export interface ReportListItem {
  report_id: string;
  created_at: string;
  path: string;
}

export interface ReportListResponse {
  total: number;
  limit: number;
  offset: number;
  reports: ReportListItem[];
}

export const researchApi = {
  triggerMarketDaily: (symbols?: string[]) =>
    apiClient.post('/research/market-daily', { symbols }).then(r => r.data),

  triggerStockResearch: (symbol: string) =>
    apiClient.post('/research/stock', { symbol }).then(r => r.data),

  getStatus: (reportId: string) =>
    apiClient.get<ResearchStatus>(`/research/status/${reportId}`).then(r => r.data),

  getReport: (reportId: string) =>
    apiClient.get<ResearchReport>(`/research/report/${reportId}`).then(r => r.data),

  listReports: (params?: { report_type?: string; limit?: number; offset?: number }) =>
    apiClient.get<ReportListResponse>('/research/reports', { params }).then(r => r.data),
};
