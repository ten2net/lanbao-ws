import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout/Layout';
import { BacktestListPage } from './pages/BacktestListPage';
import { BacktestDetailPage } from './pages/BacktestDetailPage';
import { ComparePage } from './pages/ComparePage';
import { ParamAnalysisPage } from './pages/ParamAnalysisPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<BacktestListPage />} />
            <Route path="/backtest/:backtestId" element={<BacktestDetailPage />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="/param-analysis" element={<ParamAnalysisPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
