import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppShell } from './components/AppShell/AppShell';
import { BacktestListPage } from './pages/BacktestListPage';
import { BacktestDetailPage } from './pages/BacktestDetailPage';
import { ComparePage } from './pages/ComparePage';
import { ParamAnalysisPage } from './pages/ParamAnalysisPage';
import { SystemOverviewPage } from './pages/SystemOverviewPage';
import { NodeStatusPage } from './pages/NodeStatusPage';
import { RiskMonitorPage } from './pages/RiskMonitorPage';
import { DataCenterPage } from './pages/DataCenterPage';
import { SystemConfigPage } from './pages/SystemConfigPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<BacktestListPage />} />
            <Route path="/backtest/:backtestId" element={<BacktestDetailPage />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="/param-analysis" element={<ParamAnalysisPage />} />
            <Route path="/system-overview" element={<SystemOverviewPage />} />
            <Route path="/node-status" element={<NodeStatusPage />} />
            <Route path="/risk-monitor" element={<RiskMonitorPage />} />
            <Route path="/data-center" element={<DataCenterPage />} />
            <Route path="/system-config" element={<SystemConfigPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
