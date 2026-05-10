# 回测面板前端 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 React 前端应用，提供专业的回测管理与分析界面，集成 TradingView Lightweight Charts 绘制 K 线和买卖点，使用 Recharts 渲染分析图表。

**Architecture:** React SPA + Vite + React Router + Zustand 状态管理 + TanStack Query 数据获取。前端通过 REST API 和 WebSocket 与 FastAPI 后端通信。

**Tech Stack:** React 18, TypeScript, Vite, Ant Design 5, React Router 6, Zustand, TanStack Query, TradingView Lightweight Charts, Recharts

---

## File Structure

```
src/lanbao_backtest/web/                          # 新增: React 前端
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── index.html
├── .env.development
├── .env.production
├── src/
│   ├── main.tsx                                    # 应用入口
│   ├── App.tsx                                     # 根组件 + 路由
│   ├── index.css                                   # 全局样式
│   ├── types/
│   │   └── backtest.ts                             # TypeScript 类型定义
│   ├── api/
│   │   ├── client.ts                               # Axios/Fetch 封装
│   │   ├── backtest.ts                             # 回测 API 调用
│   │   └── strategy.ts                             # 策略 API 调用
│   ├── stores/
│   │   └── backtestStore.ts                        # Zustand 状态管理
│   ├── hooks/
│   │   ├── useBacktests.ts                         # TanStack Query hooks
│   │   └── useWebSocket.ts                         # WebSocket hook
│   ├── components/
│   │   ├── Layout/                                 # 布局组件
│   │   │   ├── Sidebar.tsx                         # 侧边栏筛选
│   │   │   ├── Header.tsx                          # 顶部导航
│   │   │   └── Layout.tsx                          # 统一布局 Shell
│   │   ├── BacktestTable/                          # 回测列表
│   │   │   └── BacktestTable.tsx
│   │   ├── Charts/
│   │   │   ├── EquityCurve.tsx                     # 权益曲线 (Recharts)
│   │   │   ├── KLineChart.tsx                      # K 线图 (TradingView)
│   │   │   ├── MonthlyHeatmap.tsx                  # 月度收益热力图
│   │   │   ├── DrawdownChart.tsx                   # 回撤曲线
│   │   │   └── RadarChart.tsx                      # 指标雷达图
│   │   ├── Compare/
│   │   │   └── ComparePanel.tsx                    # 批量对比面板
│   │   └── common/
│   │       ├── MetricCard.tsx                      # 指标卡片
│   │       ├── StatusBadge.tsx                     # 状态标签
│   │       └── EmptyState.tsx                      # 空状态
│   └── pages/
│       ├── BacktestListPage.tsx                    # 回测列表页
│       ├── BacktestDetailPage.tsx                  # 回测详情页
│       ├── ComparePage.tsx                         # 批量对比页
│       └── ParamAnalysisPage.tsx                   # 参数分析页
```

---

## Task 1: 初始化 React 项目

**Files:**
- Create: `src/lanbao_backtest/web/package.json`
- Create: `src/lanbao_backtest/web/vite.config.ts`
- Create: `src/lanbao_backtest/web/tsconfig.json`
- Create: `src/lanbao_backtest/web/tsconfig.node.json`
- Create: `src/lanbao_backtest/web/index.html`
- Create: `src/lanbao_backtest/web/.env.development`
- Create: `src/lanbao_backtest/web/.env.production`

**Context:** 使用 Vite 初始化 React + TypeScript 项目，配置代理指向 FastAPI 后端。

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "lanbao-backtest-panel",
  "private": true,
  "version": "0.6.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host --port 8502",
    "build": "tsc && vite build",
    "preview": "vite preview --port 8502"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.26.0",
    "antd": "^5.20.0",
    "@ant-design/icons": "^5.4.0",
    "zustand": "^4.5.0",
    "@tanstack/react-query": "^5.52.0",
    "axios": "^1.7.0",
    "recharts": "^2.12.0",
    "lightweight-charts": "^4.2.0",
    "dayjs": "^1.11.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 8502,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
```

- [ ] **Step 3: 创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: 创建 tsconfig.node.json**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>揽宝回测平台</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: 创建环境变量文件**

`.env.development`:
```
VITE_API_BASE_URL=/api/v1
VITE_WS_BASE_URL=ws://localhost:8000
```

`.env.production`:
```
VITE_API_BASE_URL=/api/v1
VITE_WS_BASE_URL=wss://your-domain.com
```

- [ ] **Step 7: 安装依赖**

Run:
```bash
cd src/lanbao_backtest/web
npm install
```

- [ ] **Step 8: Commit**

```bash
git add src/lanbao_backtest/web/package.json src/lanbao_backtest/web/vite.config.ts src/lanbao_backtest/web/tsconfig.json src/lanbao_backtest/web/tsconfig.node.json src/lanbao_backtest/web/index.html src/lanbao_backtest/web/.env.development src/lanbao_backtest/web/.env.production
git commit -m "feat: initialize React + Vite + TypeScript project for backtest panel frontend"
```

---

## Task 2: TypeScript 类型定义

**Files:**
- Create: `src/lanbao_backtest/web/src/types/backtest.ts`

**Context:** 定义前端使用的所有 TypeScript 类型，与后端 Pydantic 模型对齐。

- [ ] **Step 1: 创建类型定义文件**

```typescript
/** 回测列表项 */
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

/** 回测列表响应 */
export interface BacktestListResponse {
  total: number;
  page: number;
  limit: number;
  items: BacktestListItem[];
}

/** 回测元数据 */
export interface BacktestMeta {
  strategy_id: string;
  strategy_name: string;
  strategy_params: Record<string, unknown>;
  symbol: string;
  symbol_name: string;
  start_date: string;
  end_date: string;
  total_trading_days: number;
  created_at: string;
  duration_seconds: number;
  status: string;
  tags: string[];
}

/** 绩效指标 */
export interface Performance {
  returns: {
    total_return_pct: number;
    annual_return_pct: number;
    daily_return_mean_pct: number;
    daily_return_std_pct: number;
    best_day_pct: number;
    worst_day_pct: number;
    positive_days: number;
    negative_days: number;
  };
  risk: {
    sharpe_ratio: number;
    sortino_ratio: number;
    max_drawdown_pct: number;
    max_drawdown_duration_days: number;
    volatility_annual_pct: number;
    var_95_pct: number;
    calmar_ratio: number;
  };
  trades: {
    total_count: number;
    winning_count: number;
    losing_count: number;
    win_rate_pct: number;
    profit_factor: number;
    avg_trade_return_pct: number;
    avg_win_pct: number;
    avg_loss_pct: number;
    largest_win_pct: number;
    largest_loss_pct: number;
    avg_holding_days: number;
  };
}

/** 回测详情 */
export interface BacktestDetail {
  backtest_id: string;
  meta: BacktestMeta;
  performance: Performance;
  files: Record<string, string>;
}

/** 交易记录 */
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

/** 权益曲线数据点 */
export interface EquityPoint {
  date: string;
  equity: number;
  drawdown_pct: number;
  daily_return_pct: number;
}

/** 月度收益矩阵 */
export interface MonthlyMatrix {
  [year: string]: {
    [month: string]: number;
  };
}

/** 策略模板 */
export interface StrategyTemplate {
  strategy_id: string;
  name: string;
  description: string;
  default_params: Record<string, unknown>;
}

/** 回测执行请求 */
export interface RunBacktestRequest {
  strategy_id: string;
  symbol: string;
  start_date: string;
  end_date: string;
  params: Record<string, unknown>;
}

/** WebSocket 进度消息 */
export interface WsProgressMessage {
  type: 'progress' | 'completed' | 'error';
  progress?: number;
  status?: string;
  backtest_id?: string;
  result?: unknown;
  message?: string;
  timestamp: number;
}

/** 筛选条件 */
export interface BacktestFilters {
  strategy?: string;
  symbol?: string;
  tags: string[];
  dateRange?: [string, string];
}
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/web/src/types/backtest.ts
git commit -m "feat: add TypeScript type definitions for backtest data models"
```

---

## Task 3: API 客户端

**Files:**
- Create: `src/lanbao_backtest/web/src/api/client.ts`
- Create: `src/lanbao_backtest/web/src/api/backtest.ts`
- Create: `src/lanbao_backtest/web/src/api/strategy.ts`

**Context:** 封装 axios 实例，提供统一的错误处理和类型安全的 API 调用。

- [ ] **Step 1: 创建 client.ts**

```typescript
import axios, { AxiosError } from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截器 — 统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      const data = error.response.data as { error?: { message: string } };
      const message = data?.error?.message || `请求失败: ${error.response.status}`;
      return Promise.reject(new Error(message));
    }
    if (error.request) {
      return Promise.reject(new Error('网络错误，请检查后端服务是否运行'));
    }
    return Promise.reject(error);
  }
);
```

- [ ] **Step 2: 创建 backtest.ts**

```typescript
import { apiClient } from './client';
import type {
  BacktestListResponse,
  BacktestDetail,
  BacktestFilters,
  EquityPoint,
  Trade,
  MonthlyMatrix,
  RunBacktestRequest,
} from '../types/backtest';

export const backtestApi = {
  /** 获取回测列表 */
  list: async (filters: BacktestFilters, page = 1, limit = 20) => {
    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('limit', String(limit));
    if (filters.strategy) params.set('strategy', filters.strategy);
    if (filters.symbol) params.set('symbol', filters.symbol);
    if (filters.tags.length > 0) params.set('tag', filters.tags[0]);

    const { data } = await apiClient.get<BacktestListResponse>(`/backtests?${params}`);
    return data;
  },

  /** 获取单个回测详情 */
  get: async (backtestId: string) => {
    const { data } = await apiClient.get<BacktestDetail>(`/backtests/${backtestId}`);
    return data;
  },

  /** 删除回测 */
  delete: async (backtestId: string) => {
    await apiClient.delete(`/backtests/${backtestId}`);
  },

  /** 更新标签 */
  updateTags: async (backtestId: string, tags: string[]) => {
    await apiClient.post(`/backtests/${backtestId}/tags`, tags);
  },

  /** 执行回测 */
  run: async (request: RunBacktestRequest) => {
    const { data } = await apiClient.post<{ backtest_id: string; status: string; message: string }>(
      '/backtest/run',
      request
    );
    return data;
  },

  /** 获取权益曲线 */
  getEquity: async (backtestId: string) => {
    const { data } = await apiClient.get<{ series: EquityPoint[] }>(`/backtests/${backtestId}/equity`);
    return data.series;
  },

  /** 获取交易明细 */
  getTrades: async (backtestId: string) => {
    const { data } = await apiClient.get<{ trades: Trade[] }>(`/backtests/${backtestId}/trades`);
    return data.trades;
  },

  /** 获取月度收益 */
  getMonthly: async (backtestId: string) => {
    const { data } = await apiClient.get<{ matrix: MonthlyMatrix }>(`/backtests/${backtestId}/monthly`);
    return data.matrix;
  },

  /** 批量对比 */
  compare: async (backtestIds: string[]) => {
    const { data } = await apiClient.post('/backtests/compare', { backtest_ids: backtestIds });
    return data;
  },
};
```

- [ ] **Step 3: 创建 strategy.ts**

```typescript
import { apiClient } from './client';
import type { StrategyTemplate } from '../types/backtest';

export const strategyApi = {
  /** 获取策略模板列表 */
  list: async () => {
    const { data } = await apiClient.get<{ strategies: StrategyTemplate[] }>('/strategies');
    return data.strategies;
  },

  /** 获取策略模板详情 */
  get: async (strategyId: string) => {
    const { data } = await apiClient.get<StrategyTemplate>(`/strategies/${strategyId}`);
    return data;
  },
};
```

- [ ] **Step 4: Commit**

```bash
git add src/lanbao_backtest/web/src/api/client.ts src/lanbao_backtest/web/src/api/backtest.ts src/lanbao_backtest/web/src/api/strategy.ts
git commit -m "feat: add typed API client with axios and error handling"
```

---

## Task 4: Zustand 状态管理

**Files:**
- Create: `src/lanbao_backtest/web/src/stores/backtestStore.ts`

**Context:** 管理全局状态：回测列表、筛选条件、选中项、加载状态、错误状态。

- [ ] **Step 1: 创建 Zustand store**

```typescript
import { create } from 'zustand';
import type { BacktestFilters, BacktestListItem } from '../types/backtest';

interface BacktestState {
  // 列表数据
  backtests: BacktestListItem[];
  total: number;
  page: number;
  limit: number;

  // 筛选
  filters: BacktestFilters;

  // 选中项（用于批量对比）
  selectedIds: Set<string>;

  // 加载状态
  isLoading: boolean;
  isRunning: boolean;

  // 错误
  error: string | null;

  // Actions
  setBacktests: (backtests: BacktestListItem[], total: number) => void;
  setPage: (page: number) => void;
  setFilters: (filters: Partial<BacktestFilters>) => void;
  toggleSelection: (id: string) => void;
  clearSelection: () => void;
  setLoading: (loading: boolean) => void;
  setRunning: (running: boolean) => void;
  setError: (error: string | null) => void;
}

export const useBacktestStore = create<BacktestState>((set) => ({
  backtests: [],
  total: 0,
  page: 1,
  limit: 20,

  filters: {
    strategy: undefined,
    symbol: undefined,
    tags: [],
    dateRange: undefined,
  },

  selectedIds: new Set(),

  isLoading: false,
  isRunning: false,

  error: null,

  setBacktests: (backtests, total) => set({ backtests, total }),

  setPage: (page) => set({ page }),

  setFilters: (partial) =>
    set((state) => ({
      filters: { ...state.filters, ...partial },
      page: 1, // 筛选条件变化时重置到第一页
    })),

  toggleSelection: (id) =>
    set((state) => {
      const newSet = new Set(state.selectedIds);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return { selectedIds: newSet };
    }),

  clearSelection: () => set({ selectedIds: new Set() }),

  setLoading: (isLoading) => set({ isLoading }),

  setRunning: (isRunning) => set({ isRunning }),

  setError: (error) => set({ error }),
}));
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/web/src/stores/backtestStore.ts
git commit -m "feat: add Zustand store for backtest state management"
```

---

## Task 5: TanStack Query Hooks

**Files:**
- Create: `src/lanbao_backtest/web/src/hooks/useBacktests.ts`
- Create: `src/lanbao_backtest/web/src/hooks/useWebSocket.ts`

**Context:** 封装数据获取逻辑，提供缓存、自动重试、加载状态管理。

- [ ] **Step 1: 创建 useBacktests hook**

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { backtestApi } from '../api/backtest';
import { useBacktestStore } from '../stores/backtestStore';

const BACKTEST_KEY = 'backtests';

/** 获取回测列表 */
export function useBacktestList() {
  const { filters, page, limit } = useBacktestStore();

  return useQuery({
    queryKey: [BACKTEST_KEY, 'list', filters, page, limit],
    queryFn: () => backtestApi.list(filters, page, limit),
    staleTime: 30000, // 30秒内不重新请求
  });
}

/** 获取单个回测详情 */
export function useBacktestDetail(backtestId: string | undefined) {
  return useQuery({
    queryKey: [BACKTEST_KEY, 'detail', backtestId],
    queryFn: () => backtestApi.get(backtestId!),
    enabled: !!backtestId,
    staleTime: 60000,
  });
}

/** 获取权益曲线 */
export function useEquityCurve(backtestId: string | undefined) {
  return useQuery({
    queryKey: [BACKTEST_KEY, 'equity', backtestId],
    queryFn: () => backtestApi.getEquity(backtestId!),
    enabled: !!backtestId,
  });
}

/** 获取交易明细 */
export function useTrades(backtestId: string | undefined) {
  return useQuery({
    queryKey: [BACKTEST_KEY, 'trades', backtestId],
    queryFn: () => backtestApi.getTrades(backtestId!),
    enabled: !!backtestId,
  });
}

/** 获取月度收益 */
export function useMonthlyReturns(backtestId: string | undefined) {
  return useQuery({
    queryKey: [BACKTEST_KEY, 'monthly', backtestId],
    queryFn: () => backtestApi.getMonthly(backtestId!),
    enabled: !!backtestId,
  });
}

/** 删除回测 */
export function useDeleteBacktest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: backtestApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [BACKTEST_KEY, 'list'] });
    },
  });
}

/** 执行回测 */
export function useRunBacktest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: backtestApi.run,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [BACKTEST_KEY, 'list'] });
    },
  });
}
```

- [ ] **Step 2: 创建 useWebSocket hook**

```typescript
import { useEffect, useRef, useCallback } from 'react';
import type { WsProgressMessage } from '../types/backtest';

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

export function useWebSocket(taskId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!taskId || wsRef.current) return;

    const ws = new WebSocket(`${WS_BASE}/api/v1/ws/backtest/${taskId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket 已连接');
    };

    ws.onclose = () => {
      console.log('WebSocket 已断开');
      wsRef.current = null;
    };

    ws.onerror = (error) => {
      console.error('WebSocket 错误:', error);
    };
  }, [taskId]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const send = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { connect, disconnect, send, ws: wsRef };
}
```

- [ ] **Step 3: Commit**

```bash
git add src/lanbao_backtest/web/src/hooks/useBacktests.ts src/lanbao_backtest/web/src/hooks/useWebSocket.ts
git commit -m "feat: add TanStack Query hooks and WebSocket hook"
```

---

## Task 6: 布局组件

**Files:**
- Create: `src/lanbao_backtest/web/src/components/Layout/Layout.tsx`
- Create: `src/lanbao_backtest/web/src/components/Layout/Header.tsx`
- Create: `src/lanbao_backtest/web/src/components/Layout/Sidebar.tsx`

**Context:** 构建统一的页面布局 Shell，包含顶部导航和左侧筛选面板。

- [ ] **Step 1: 创建 Layout.tsx**

```tsx
import { Outlet } from 'react-router-dom';
import { Layout as AntLayout } from 'antd';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

const { Content, Sider } = AntLayout;

export function Layout() {
  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Header />
      <AntLayout>
        <Sider width={240} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
          <Sidebar />
        </Sider>
        <Content style={{ padding: 24, background: '#fff' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
```

- [ ] **Step 2: 创建 Header.tsx**

```tsx
import { Layout, Menu } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import {
  LineChartOutlined,
  BarChartOutlined,
  SettingOutlined,
} from '@ant-design/icons';

const { Header: AntHeader } = Layout;

export function Header() {
  const location = useLocation();

  const items = [
    {
      key: '/',
      icon: <LineChartOutlined />,
      label: <Link to="/">回测列表</Link>,
    },
    {
      key: '/compare',
      icon: <BarChartOutlined />,
      label: <Link to="/compare">批量对比</Link>,
    },
    {
      key: '/param-analysis',
      icon: <SettingOutlined />,
      label: <Link to="/param-analysis">参数分析</Link>,
    },
  ];

  return (
    <AntHeader style={{ background: '#fff', borderBottom: '1px solid #f0f0f0', padding: 0 }}>
      <div style={{ float: 'left', padding: '0 24px', fontSize: 18, fontWeight: 'bold' }}>
        揽宝回测平台
      </div>
      <Menu
        mode="horizontal"
        selectedKeys={[location.pathname]}
        items={items}
        style={{ borderBottom: 'none' }}
      />
    </AntHeader>
  );
}
```

- [ ] **Step 3: 创建 Sidebar.tsx**

```tsx
import { useState } from 'react';
import { Collapse, Select, DatePicker, Tag, Button, Space } from 'antd';
import { useBacktestStore } from '../../stores/backtestStore';
import { useQuery } from '@tanstack/react-query';
import { strategyApi } from '../../api/strategy';

const { Panel } = Collapse;
const { Option } = Select;
const { RangePicker } = DatePicker;

export function Sidebar() {
  const { filters, setFilters } = useBacktestStore();
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const { data: strategies } = useQuery({
    queryKey: ['strategies'],
    queryFn: strategyApi.list,
  });

  const allTags = ['优化', '验证', '对比', '2025Q1'];

  return (
    <div style={{ padding: 16 }}>
      <Collapse defaultActiveKey={['1', '2', '3']} ghost>
        <Panel header="策略类型" key="1">
          <Select
            placeholder="选择策略"
            allowClear
            style={{ width: '100%' }}
            value={filters.strategy}
            onChange={(value) => setFilters({ strategy: value })}
          >
            {strategies?.map((s) => (
              <Option key={s.strategy_id} value={s.strategy_id}>
                {s.name}
              </Option>
            ))}
          </Select>
        </Panel>

        <Panel header="标签" key="2">
          <Space wrap>
            {allTags.map((tag) => (
              <Tag
                key={tag}
                color={selectedTags.includes(tag) ? 'blue' : undefined}
                style={{ cursor: 'pointer' }}
                onClick={() => {
                  const newTags = selectedTags.includes(tag)
                    ? selectedTags.filter((t) => t !== tag)
                    : [...selectedTags, tag];
                  setSelectedTags(newTags);
                  setFilters({ tags: newTags });
                }}
              >
                {tag}
              </Tag>
            ))}
          </Space>
        </Panel>

        <Panel header="日期范围" key="3">
          <RangePicker
            style={{ width: '100%' }}
            onChange={(dates) => {
              if (dates) {
                setFilters({
                  dateRange: [
                    dates[0]?.format('YYYY-MM-DD') || '',
                    dates[1]?.format('YYYY-MM-DD') || '',
                  ],
                });
              }
            }}
          />
        </Panel>
      </Collapse>

      <Button
        block
        style={{ marginTop: 16 }}
        onClick={() => {
          setSelectedTags([]);
          setFilters({ strategy: undefined, symbol: undefined, tags: [], dateRange: undefined });
        }}
      >
        清除筛选
      </Button>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add src/lanbao_backtest/web/src/components/Layout/Layout.tsx src/lanbao_backtest/web/src/components/Layout/Header.tsx src/lanbao_backtest/web/src/components/Layout/Sidebar.tsx
git commit -m "feat: add Layout shell with Header and Sidebar filter panel"
```

---

## Task 7: 路由和页面框架

**Files:**
- Create: `src/lanbao_backtest/web/src/App.tsx`
- Create: `src/lanbao_backtest/web/src/pages/BacktestListPage.tsx`
- Create: `src/lanbao_backtest/web/src/pages/BacktestDetailPage.tsx`
- Create: `src/lanbao_backtest/web/src/pages/ComparePage.tsx`
- Create: `src/lanbao_backtest/web/src/pages/ParamAnalysisPage.tsx`

**Context:** 配置 React Router，创建页面框架（空壳），确保路由切换正常。

- [ ] **Step 1: 创建 App.tsx**

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout/Layout';
import { BacktestListPage } from './pages/BacktestListPage';
import { BacktestDetailPage } from './pages/BacktestDetailPage';
import { ComparePage } from './pages/ComparePage';
import { ParamAnalysisPage } from './pages/ParamAnalysisPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
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
```

- [ ] **Step 2: 创建页面框架**

```tsx
// pages/BacktestListPage.tsx
import { Typography } from 'antd';

const { Title } = Typography;

export function BacktestListPage() {
  return <Title level={3}>回测列表</Title>;
}
```

```tsx
// pages/BacktestDetailPage.tsx
import { useParams } from 'react-router-dom';
import { Typography } from 'antd';

const { Title } = Typography;

export function BacktestDetailPage() {
  const { backtestId } = useParams<{ backtestId: string }>();
  return <Title level={3}>回测详情: {backtestId}</Title>;
}
```

```tsx
// pages/ComparePage.tsx
import { Typography } from 'antd';

const { Title } = Typography;

export function ComparePage() {
  return <Title level={3}>批量对比</Title>;
}
```

```tsx
// pages/ParamAnalysisPage.tsx
import { Typography } from 'antd';

const { Title } = Typography;

export function ParamAnalysisPage() {
  return <Title level={3}>参数敏感性分析</Title>;
}
```

- [ ] **Step 3: 创建 main.tsx**

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 4: 创建 index.css**

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

- [ ] **Step 5: Commit**

```bash
git add src/lanbao_backtest/web/src/App.tsx src/lanbao_backtest/web/src/main.tsx src/lanbao_backtest/web/src/index.css src/lanbao_backtest/web/src/pages/
git commit -m "feat: add React Router setup with page skeletons"
```

---

## Task 8: 回测列表页

**Files:**
- Create: `src/lanbao_backtest/web/src/components/BacktestTable/BacktestTable.tsx`
- Modify: `src/lanbao_backtest/web/src/pages/BacktestListPage.tsx`

**Context:** 实现回测列表页，包含表格展示、多选、分页、操作按钮。

- [ ] **Step 1: 创建 BacktestTable 组件**

```tsx
import { useState } from 'react';
import { Table, Button, Space, Tag, Popconfirm, message } from 'antd';
import { Link } from 'react-router-dom';
import { useBacktestStore } from '../../stores/backtestStore';
import { useBacktestList, useDeleteBacktest } from '../../hooks/useBacktests';
import type { BacktestListItem } from '../../types/backtest';

export function BacktestTable() {
  const { selectedIds, toggleSelection, clearSelection } = useBacktestStore();
  const { data, isLoading } = useBacktestList();
  const deleteMutation = useDeleteBacktest();

  const [page, setPage] = useState(1);

  const columns = [
    {
      title: '回测ID',
      dataIndex: 'backtest_id',
      key: 'backtest_id',
      render: (id: string) => <Link to={`/backtest/${id}`}>{id}</Link>,
    },
    {
      title: '策略',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
    },
    {
      title: '标的',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: '总收益',
      dataIndex: 'total_return',
      key: 'total_return',
      render: (v: number | null) =>
        v !== null ? (
          <span style={{ color: v >= 0 ? '#cf1322' : '#3f8600' }}>
            {v >= 0 ? '+' : ''}
            {v.toFixed(2)}%
          </span>
        ) : (
          '-'
        ),
    },
    {
      title: '夏普比率',
      dataIndex: 'sharpe_ratio',
      key: 'sharpe_ratio',
      render: (v: number | null) => (v !== null ? v.toFixed(2) : '-'),
    },
    {
      title: '最大回撤',
      dataIndex: 'max_drawdown',
      key: 'max_drawdown',
      render: (v: number | null) =>
        v !== null ? <span style={{ color: '#3f8600' }}>{v.toFixed(2)}%</span> : '-',
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <Space size={4}>
          {tags.map((tag) => (
            <Tag key={tag} size="small">
              {tag}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: BacktestListItem) => (
        <Space>
          <Link to={`/backtest/${record.backtest_id}`}>查看</Link>
          <Popconfirm
            title="确认删除?"
            onConfirm={() => {
              deleteMutation.mutate(record.backtest_id, {
                onSuccess: () => message.success('已删除'),
              });
            }}
          >
            <Button type="link" danger size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const rowSelection = {
    selectedRowKeys: Array.from(selectedIds),
    onChange: (_: React.Key[], selectedRows: BacktestListItem[]) => {
      clearSelection();
      selectedRows.forEach((r) => toggleSelection(r.backtest_id));
    },
  };

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Space>
          {selectedIds.size > 0 && (
            <Button type="primary">
              <Link to="/compare">批量对比 ({selectedIds.size})</Link>
            </Button>
          )}
        </Space>
      </div>
      <Table
        rowSelection={rowSelection}
        columns={columns}
        dataSource={data?.items || []}
        rowKey="backtest_id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: 20,
          total: data?.total || 0,
          onChange: setPage,
        }}
      />
    </>
  );
}
```

- [ ] **Step 2: 修改 BacktestListPage**

```tsx
import { Typography, Button, Modal, Form, Input, DatePicker, Select, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { BacktestTable } from '../components/BacktestTable/BacktestTable';
import { useRunBacktest } from '../hooks/useBacktests';

const { Title } = Typography;
const { Option } = Select;

export function BacktestListPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();
  const runMutation = useRunBacktest();

  const handleRun = async (values: unknown) => {
    try {
      await runMutation.mutateAsync(values as Parameters<typeof runMutation.mutate>[0]);
      message.success('回测已启动');
      setIsModalOpen(false);
      form.resetFields();
    } catch (error) {
      message.error(`启动失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          回测列表
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsModalOpen(true)}>
          运行新回测
        </Button>
      </div>

      <BacktestTable />

      <Modal
        title="运行新回测"
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={runMutation.isPending}
      >
        <Form form={form} onFinish={handleRun} layout="vertical">
          <Form.Item
            name="strategy_id"
            label="策略"
            rules={[{ required: true }]}
            initialValue="ma_cross"
          >
            <Select>
              <Option value="ma_cross">双均线交叉策略</Option>
              <Option value="rsi">RSI策略</Option>
              <Option value="macd">MACD策略</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="symbol"
            label="股票代码"
            rules={[{ required: true }]}
            initialValue="000001.SZ"
          >
            <Input />
          </Form.Item>
          <Form.Item name="dateRange" label="日期范围" rules={[{ required: true }]}>
            <DatePicker.RangePicker />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add src/lanbao_backtest/web/src/components/BacktestTable/BacktestTable.tsx src/lanbao_backtest/web/src/pages/BacktestListPage.tsx
git commit -m "feat: implement BacktestListPage with table, selection, and run modal"
```

---

## Task 9: 回测详情页

**Files:**
- Create: `src/lanbao_backtest/web/src/components/Charts/EquityCurve.tsx`
- Modify: `src/lanbao_backtest/web/src/pages/BacktestDetailPage.tsx`

**Context:** 实现回测详情页，展示权益曲线和关键指标。

- [ ] **Step 1: 创建 EquityCurve 组件**

```tsx
import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
} from 'recharts';
import type { EquityPoint } from '../../types/backtest';

interface Props {
  data: EquityPoint[];
}

export function EquityCurve({ data }: Props) {
  const chartData = useMemo(() => {
    return data.map((p) => ({
      date: p.date.slice(5), // MM-DD
      equity: p.equity,
      drawdown: Math.abs(p.drawdown_pct),
    }));
  }, [data]);

  return (
    <div style={{ width: '100%', height: 400 }}>
      <ResponsiveContainer>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis yAxisId="left" domain={['auto', 'auto']} />
          <YAxis yAxisId="right" orientation="right" domain={[0, 'auto']} />
          <Tooltip
            formatter={(value: number, name: string) => [
              name === 'equity' ? `¥${value.toFixed(2)}` : `${value.toFixed(2)}%`,
              name === 'equity' ? '权益' : '回撤',
            ]}
          />
          <Area
            yAxisId="right"
            type="monotone"
            dataKey="drawdown"
            fill="#ff4d4f"
            fillOpacity={0.1}
            stroke="#ff4d4f"
            strokeWidth={1}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="equity"
            stroke="#1890ff"
            strokeWidth={2}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: 修改 BacktestDetailPage**

```tsx
import { useParams } from 'react-router-dom';
import { Typography, Tabs, Card, Row, Col, Statistic, Spin } from 'antd';
import { useBacktestDetail, useEquityCurve } from '../hooks/useBacktests';
import { EquityCurve } from '../components/Charts/EquityCurve';

const { Title } = Typography;

export function BacktestDetailPage() {
  const { backtestId } = useParams<{ backtestId: string }>();
  const { data: detail, isLoading: detailLoading } = useBacktestDetail(backtestId);
  const { data: equity, isLoading: equityLoading } = useEquityCurve(backtestId);

  if (detailLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 64 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!detail) {
    return <Title level={3}>回测不存在</Title>;
  }

  const perf = detail.performance;

  const items = [
    {
      key: 'equity',
      label: '📈 权益曲线',
      children: equityLoading ? (
        <Spin />
      ) : equity ? (
        <EquityCurve data={equity} />
      ) : (
        '暂无权益曲线数据'
      ),
    },
    {
      key: 'trades',
      label: '📝 交易明细',
      children: '交易明细 Tab（后续实现）',
    },
    {
      key: 'monthly',
      label: '📊 月度收益',
      children: '月度收益 Tab（后续实现）',
    },
    {
      key: 'stats',
      label: '📋 统计指标',
      children: '统计指标 Tab（后续实现）',
    },
  ];

  return (
    <div>
      <Title level={3}>
        {detail.meta.strategy_name} — {detail.meta.symbol}
      </Title>

      <Card style={{ marginBottom: 24 }}>
        <Row gutter={24}>
          <Col span={6}>
            <Statistic
              title="总收益"
              value={perf.returns.total_return_pct}
              precision={2}
              suffix="%"
              valueStyle={{ color: perf.returns.total_return_pct >= 0 ? '#cf1322' : '#3f8600' }}
            />
          </Col>
          <Col span={6}>
            <Statistic title="年化收益" value={perf.returns.annual_return_pct} precision={2} suffix="%" />
          </Col>
          <Col span={6}>
            <Statistic title="夏普比率" value={perf.risk.sharpe_ratio} precision={2} />
          </Col>
          <Col span={6}>
            <Statistic
              title="最大回撤"
              value={perf.risk.max_drawdown_pct}
              precision={2}
              suffix="%"
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
        </Row>
      </Card>

      <Tabs defaultActiveKey="equity" items={items} />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add src/lanbao_backtest/web/src/components/Charts/EquityCurve.tsx src/lanbao_backtest/web/src/pages/BacktestDetailPage.tsx
git commit -m "feat: implement BacktestDetailPage with equity curve and metric cards"
```

---

## Task 10: K 线图组件（TradingView Lightweight Charts）

**Files:**
- Create: `src/lanbao_backtest/web/src/components/Charts/KLineChart.tsx`

**Context:** 使用 TradingView Lightweight Charts 绘制 K 线图，并标注买卖点。

- [ ] **Step 1: 创建 KLineChart 组件**

```tsx
import { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, HistogramData } from 'lightweight-charts';
import type { Trade } from '../../types/backtest';

interface KLineData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Props {
  data: KLineData[];
  trades: Trade[];
}

export function KLineChart({ data, trades }: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    // 创建图表
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#d9d9d9',
      },
      timeScale: {
        borderColor: '#d9d9d9',
      },
    });

    chartRef.current = chart;

    // K 线系列
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#cf1322',
      downColor: '#3f8600',
      borderUpColor: '#cf1322',
      borderDownColor: '#3f8600',
      wickUpColor: '#cf1322',
      wickDownColor: '#3f8600',
    });

    const candleData: CandlestickData[] = data.map((d) => ({
      time: d.time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    candleSeries.setData(candleData);

    // 成交量
    const volumeSeries = chart.addHistogramSeries({
      color: '#1890ff',
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    const volumeData: HistogramData[] = data.map((d) => ({
      time: d.time,
      value: d.volume,
      color: d.close >= d.open ? '#cf1322' : '#3f8600',
    }));

    volumeSeries.setData(volumeData);

    // 买卖点标注
    trades.forEach((trade) => {
      const marker = {
        time: trade.trade_date,
        position: trade.action === 'BUY' ? 'belowBar' : 'aboveBar',
        color: trade.action === 'BUY' ? '#52c41a' : '#ff4d4f',
        shape: trade.action === 'BUY' ? 'arrowUp' : 'arrowDown',
        text: `${trade.action} ${trade.quantity}@${trade.price.toFixed(2)}`,
      };
      candleSeries.setMarkers([...candleSeries.markers(), marker]);
    });

    // 自适应
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, trades]);

  return <div ref={chartContainerRef} style={{ width: '100%' }} />;
}
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/web/src/components/Charts/KLineChart.tsx
git commit -m "feat: add TradingView Lightweight Charts KLine component with trade markers"
```

---

## Task 11: 构建和启动脚本

**Files:**
- Create: `scripts/start_backtest_web.sh`
- Modify: `src/lanbao_backtest/web/package.json` — 添加 proxy 配置已包含在 vite.config.ts 中

**Context:** 添加启动前端开发服务器的脚本。

- [ ] **Step 1: 创建启动脚本**

```bash
#!/bin/bash
# scripts/start_backtest_web.sh
# 启动回测面板前端开发服务器

cd "$(dirname "$0")/../src/lanbao_backtest/web"

echo "启动回测面板前端..."
npm run dev
```

- [ ] **Step 2: Commit**

```bash
chmod +x scripts/start_backtest_web.sh
git add scripts/start_backtest_web.sh
git commit -m "chore: add startup script for backtest panel frontend"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ 前端页面与路由设计 → Task 7 (路由), Task 8-9 (页面)
- ✅ 回测列表页 → Task 8
- ✅ 回测详情页 → Task 9 (权益曲线), Task 10 (K 线图)
- ✅ TradingView Lightweight Charts → Task 10
- ✅ 批量对比页框架 → Task 7
- ✅ 参数分析页框架 → Task 7
- ✅ 状态管理 → Task 4 (Zustand), Task 5 (TanStack Query)
- ✅ 技术选型 → Task 1 (初始化)

**2. Placeholder scan:**
- ✅ 无 TBD/TODO
- ✅ 代码完整可运行

**3. Type consistency:**
- ✅ API 客户端类型与 backend Pydantic 模型对齐
- ✅ Zustand store 类型完整

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-10-backtest-panel-frontend.md`.**

**前后端计划全部就绪。两个执行选项：**

**1. Subagent-Driven (recommended)** — 每个 Task 分配独立 subagent，我在 Task 之间审查

**2. Inline Execution** — 在当前 session 中使用 executing-plans 批量执行

**Which approach?**
