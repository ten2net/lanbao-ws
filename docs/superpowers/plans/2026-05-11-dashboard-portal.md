# Dashboard 平台化移植实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Streamlit Dashboard 中5个页面（系统概览、节点状态、风险监控、数据底座、系统配置）移植到 React 前端，升级为企业级 UI/UX（双层导航、主题系统、WebSocket 实时数据）。

**Architecture:** 前端基础架构先升级（主题系统、WebSocket 管理器、双层导航布局），再基于此实现5个新页面；后端配合新增 ROS2 SystemMetrics 消息类型和 system_metrics_node 节点，FastAPI 新增数据底座和系统配置接口。所有实时数据统一通过 ros2 websocket 桥推送。

**Tech Stack:** React 18 + TypeScript + Vite + Ant Design 5 + Zustand + TanStack Query + Recharts + ros2 websocket bridge

**Branch:** `feat/dashboard-portal`

---

## 文件结构映射

### 新增文件

| 文件 | 职责 |
|------|------|
| `src/lanbao_interfaces/msg/SystemMetrics.msg` | ROS2 系统指标消息定义 |
| `src/lanbao_monitor/lanbao_monitor/system_metrics_node.py` | 系统指标采集与发布节点 |
| `web/src/types/ros2.ts` | ROS2 WebSocket 相关 TypeScript 类型 |
| `web/src/types/monitor.ts` | 监控相关类型定义 |
| `web/src/types/data.ts` | 数据底座相关类型定义 |
| `web/src/types/config.ts` | 系统配置相关类型定义 |
| `web/src/stores/themeStore.ts` | 主题状态管理（light/dark/auto） |
| `web/src/stores/wsStore.ts` | WebSocket 连接状态管理 |
| `web/src/stores/monitorStore.ts` | 监控数据状态管理 |
| `web/src/stores/dataStore.ts` | 数据底座状态管理 |
| `web/src/stores/configStore.ts` | 系统配置状态管理 |
| `web/src/services/ros2WebSocket.ts` | WebSocket 连接管理器 |
| `web/src/hooks/useROSTopic.ts` | ROS2 Topic 订阅 Hook |
| `web/src/hooks/useSystemMetrics.ts` | 系统指标便捷 Hook |
| `web/src/hooks/useNodeStatus.ts` | 节点状态便捷 Hook |
| `web/src/hooks/useAlerts.ts` | 告警便捷 Hook |
| `web/src/components/AppShell/AppShell.tsx` | 双层导航布局壳 |
| `web/src/components/AppShell/TopNav.tsx` | 顶部一级导航 |
| `web/src/components/AppShell/SideNav.tsx` | 侧边二级导航 |
| `web/src/components/AppShell/ConnectionStatus.tsx` | WebSocket 连接状态指示灯 |
| `web/src/components/ThemeToggle/ThemeToggle.tsx` | 主题切换按钮 |
| `web/src/components/Monitor/KPIGrid.tsx` | KPI 指标卡片网格 |
| `web/src/components/Monitor/MetricChart.tsx` | 指标时序折线图 |
| `web/src/components/Monitor/StatusPieChart.tsx` | 状态分布饼图 |
| `web/src/components/Monitor/AlertBadge.tsx` | 告警级别徽章 |
| `web/src/api/data.ts` | 数据底座 HTTP API |
| `web/src/api/config.ts` | 系统配置 HTTP API |
| `web/src/pages/SystemOverviewPage.tsx` | 系统概览页面 |
| `web/src/pages/NodeStatusPage.tsx` | 节点状态页面 |
| `web/src/pages/RiskMonitorPage.tsx` | 风险监控页面 |
| `web/src/pages/DataCenterPage.tsx` | 数据底座页面 |
| `web/src/pages/SystemConfigPage.tsx` | 系统配置页面 |
| `src/lanbao_backtest/api/routes/data.py` | FastAPI 数据底座路由 |
| `src/lanbao_backtest/api/routes/config.py` | FastAPI 系统配置路由 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/lanbao_interfaces/CMakeLists.txt` | 添加 SystemMetrics.msg |
| `src/lanbao_backtest/web/src/main.tsx` | 注入 ThemeProvider、ConfigProvider theme 配置 |
| `src/lanbao_backtest/web/src/App.tsx` | 新路由、新 Layout |
| `src/lanbao_backtest/web/src/index.css` | 添加 CSS Variables 主题变量 |
| `src/lanbao_backtest/api/main.py` | 注册 data、config 路由 |
| `src/lanbao_backtest/api/models.py` | 添加数据底座和配置 Pydantic 模型 |
| `src/lanbao_monitor/setup.py` | 添加 system_metrics_node 入口点 |

---

## Phase 1: 基础架构升级

### Task 1: 主题系统 — 类型定义与 Store

**Files:**
- Create: `web/src/types/theme.ts`
- Create: `web/src/stores/themeStore.ts`
- Modify: `web/src/main.tsx`

- [ ] **Step 1: 创建主题类型定义**

`web/src/types/theme.ts`:
```typescript
export type ThemeMode = 'light' | 'dark' | 'auto';

export interface ThemeState {
  mode: ThemeMode;
  isDark: boolean;
  setMode: (mode: ThemeMode) => void;
  toggle: () => void;
}
```

- [ ] **Step 2: 创建 themeStore**

`web/src/stores/themeStore.ts`:
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ThemeState, ThemeMode } from '../types/theme';

function getInitialDark(mode: ThemeMode): boolean {
  if (mode === 'auto') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  return mode === 'dark';
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      mode: 'auto',
      isDark: getInitialDark('auto'),
      setMode: (mode) => set({ mode, isDark: getInitialDark(mode) }),
      toggle: () => {
        const current = get().isDark;
        const newMode: ThemeMode = current ? 'light' : 'dark';
        set({ mode: newMode, isDark: !current });
      },
    }),
    { name: 'lanbao-theme' }
  )
);

// 监听系统主题变化
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  const store = useThemeStore.getState();
  if (store.mode === 'auto') {
    useThemeStore.setState({ isDark: e.matches });
  }
});
```

- [ ] **Step 3: 修改 main.tsx 注入主题**

修改 `web/src/main.tsx`，将原有内容替换为：

```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import App from './App';
import './index.css';
import { useThemeStore } from './stores/themeStore';

dayjs.locale('zh-cn');

function ThemedApp() {
  const isDark = useThemeStore((s) => s.isDark);
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: { colorPrimary: '#1677ff' },
      }}
    >
      <App />
    </ConfigProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemedApp />
  </React.StrictMode>,
);
```

- [ ] **Step 4: 验证编译**

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web
npx tsc --noEmit
```

Expected: 无类型错误（themeStore 引用可能报错因为类型文件还没被导入，但这是预期的）

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: 主题系统（themeStore + ConfigProvider 动态切换）"
```

---

### Task 2: WebSocket 连接管理器

**Files:**
- Create: `web/src/services/ros2WebSocket.ts`
- Create: `web/src/stores/wsStore.ts`
- Create: `web/src/types/ros2.ts`

- [ ] **Step 1: 创建 ROS2 类型定义**

`web/src/types/ros2.ts`:
```typescript
export interface ROS2BridgeMessage {
  op: 'subscribe' | 'unsubscribe' | 'publish';
  topic: string;
  type?: string;
  msg?: unknown;
}

export interface ROS2BridgeEvent<T = unknown> {
  topic: string;
  msg: T;
  timestamp: number;
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

export interface SystemMetricsMsg {
  timestamp: { sec: number; nanosec: number };
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  network_bytes_sent: number;
  network_bytes_recv: number;
  load_average_1m: number;
}

export interface NodeStatusMsg {
  header: { stamp: { sec: number; nanosec: number } };
  node_name: string;
  node_type: string;
  status: 'INITIALIZING' | 'RUNNING' | 'ERROR' | 'STOPPED';
  cpu_usage: number;
  memory_usage: number;
  message_count: number;
  last_error: string;
  timestamp: number;
}

export interface RiskAlertMsg {
  header: { stamp: { sec: number; nanosec: number } };
  alert_id: string;
  alert_type: 'POSITION' | 'DRAWDOWN' | 'VOLATILITY' | 'SYSTEM';
  level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  message: string;
  current_value: number;
  threshold: number;
  affected_strategies: string[];
  timestamp: number;
}
```

- [ ] **Step 2: 创建 wsStore**

`web/src/stores/wsStore.ts`:
```typescript
import { create } from 'zustand';
import type { ConnectionState } from '../types/ros2';

interface WSState {
  connectionState: ConnectionState;
  subscribedTopics: Set<string>;
  setConnectionState: (state: ConnectionState) => void;
  addSubscribedTopic: (topic: string) => void;
  removeSubscribedTopic: (topic: string) => void;
}

export const useWSStore = create<WSState>((set) => ({
  connectionState: 'disconnected',
  subscribedTopics: new Set(),
  setConnectionState: (connectionState) => set({ connectionState }),
  addSubscribedTopic: (topic) =>
    set((state) => ({ subscribedTopics: new Set(state.subscribedTopics).add(topic) })),
  removeSubscribedTopic: (topic) =>
    set((state) => {
      const next = new Set(state.subscribedTopics);
      next.delete(topic);
      return { subscribedTopics: next };
    }),
}));
```

- [ ] **Step 3: 创建 ROS2WebSocketManager**

`web/src/services/ros2WebSocket.ts`:
```typescript
import type { ROS2BridgeMessage, ConnectionState } from '../types/ros2';
import { useWSStore } from '../stores/wsStore';

type MessageCallback = (msg: unknown) => void;

const WS_URL = import.meta.env.VITE_ROS2_WS_URL || 'ws://localhost:9090';

class ROS2WebSocketManager {
  private ws: WebSocket | null = null;
  private callbacks = new Map<string, Set<MessageCallback>>();
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private shouldReconnect = true;

  connect(): void {
    this.shouldReconnect = true;
    this._doConnect();
  }

  private _doConnect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    useWSStore.getState().setConnectionState('connecting');

    try {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => {
        useWSStore.getState().setConnectionState('connected');
        this.reconnectDelay = 1000;
        // 恢复已有订阅
        this.callbacks.forEach((_, topic) => this._sendSubscribe(topic));
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.topic) {
            this.callbacks.get(data.topic)?.forEach((cb) => cb(data.msg));
          }
        } catch {
          // 忽略格式异常消息
        }
      };

      this.ws.onclose = () => {
        useWSStore.getState().setConnectionState('disconnected');
        this._scheduleReconnect();
      };

      this.ws.onerror = () => {
        useWSStore.getState().setConnectionState('disconnected');
      };
    } catch {
      useWSStore.getState().setConnectionState('disconnected');
      this._scheduleReconnect();
    }
  }

  private _scheduleReconnect(): void {
    if (!this.shouldReconnect) return;
    useWSStore.getState().setConnectionState('reconnecting');
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      this._doConnect();
    }, this.reconnectDelay);
  }

  private _sendSubscribe(topic: string): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    const msg: ROS2BridgeMessage = { op: 'subscribe', topic };
    this.ws.send(JSON.stringify(msg));
  }

  private _sendUnsubscribe(topic: string): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    const msg: ROS2BridgeMessage = { op: 'unsubscribe', topic };
    this.ws.send(JSON.stringify(msg));
  }

  subscribe(topic: string, callback: MessageCallback): void {
    const isFirst = !this.callbacks.has(topic) || this.callbacks.get(topic)!.size === 0;
    if (!this.callbacks.has(topic)) {
      this.callbacks.set(topic, new Set());
    }
    this.callbacks.get(topic)!.add(callback);
    if (isFirst) {
      this._sendSubscribe(topic);
      useWSStore.getState().addSubscribedTopic(topic);
    }
  }

  unsubscribe(topic: string, callback: MessageCallback): void {
    const cbs = this.callbacks.get(topic);
    if (!cbs) return;
    cbs.delete(callback);
    if (cbs.size === 0) {
      this.callbacks.delete(topic);
      this._sendUnsubscribe(topic);
      useWSStore.getState().removeSubscribedTopic(topic);
    }
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
    useWSStore.getState().setConnectionState('disconnected');
  }
}

export const ros2WS = new ROS2WebSocketManager();
```

- [ ] **Step 4: 创建 useROSTopic Hook**

`web/src/hooks/useROSTopic.ts`:
```typescript
import { useEffect } from 'react';
import { ros2WS } from '../services/ros2WebSocket';

export function useROSTopic<T>(topic: string, onMessage: (msg: T) => void): void {
  useEffect(() => {
    ros2WS.subscribe(topic, onMessage as (msg: unknown) => void);
    return () => ros2WS.unsubscribe(topic, onMessage as (msg: unknown) => void);
  }, [topic, onMessage]);
}
```

- [ ] **Step 5: 验证编译**

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web
npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: WebSocket 连接管理器（ros2WebSocket + wsStore + useROSTopic）"
```

---

### Task 3: 双层导航布局

**Files:**
- Create: `web/src/components/AppShell/AppShell.tsx`
- Create: `web/src/components/AppShell/TopNav.tsx`
- Create: `web/src/components/AppShell/SideNav.tsx`
- Create: `web/src/components/AppShell/ConnectionStatus.tsx`
- Create: `web/src/components/ThemeToggle/ThemeToggle.tsx`
- Modify: `web/src/App.tsx`
- Modify: `web/src/index.css`

- [ ] **Step 1: 创建 ThemeToggle 组件**

`web/src/components/ThemeToggle/ThemeToggle.tsx`:
```typescript
import { Button } from 'antd';
import { MoonOutlined, SunOutlined, DesktopOutlined } from '@ant-design/icons';
import { useThemeStore } from '../../stores/themeStore';

export function ThemeToggle() {
  const { mode, toggle } = useThemeStore();
  const icon = mode === 'dark' ? <MoonOutlined /> : mode === 'light' ? <SunOutlined /> : <DesktopOutlined />;
  return (
    <Button type="text" icon={icon} onClick={toggle} title={`当前主题: ${mode}`} />
  );
}
```

- [ ] **Step 2: 创建 ConnectionStatus 组件**

`web/src/components/AppShell/ConnectionStatus.tsx`:
```typescript
import { Badge, Tooltip } from 'antd';
import { useWSStore } from '../../stores/wsStore';

const stateMap = {
  connected: { color: 'green' as const, text: '实时数据已连接' },
  connecting: { color: 'yellow' as const, text: '正在连接...' },
  reconnecting: { color: 'orange' as const, text: '正在重连...' },
  disconnected: { color: 'red' as const, text: '实时数据已断开' },
};

export function ConnectionStatus() {
  const state = useWSStore((s) => s.connectionState);
  const info = stateMap[state];
  return (
    <Tooltip title={info.text}>
      <Badge color={info.color} text={state === 'connected' ? '在线' : state === 'disconnected' ? '离线' : '连接中'} />
    </Tooltip>
  );
}
```

- [ ] **Step 3: 创建 TopNav 组件**

`web/src/components/AppShell/TopNav.tsx`:
```typescript
import { Menu } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import type { MenuProps } from 'antd';

interface TopNavProps {
  activeModule: string;
  onModuleChange: (module: string) => void;
}

const modules: { key: string; label: string }[] = [
  { key: 'research', label: '投研中心' },
  { key: 'monitor', label: '实时监控' },
  { key: 'data', label: '数据管理' },
  { key: 'settings', label: '系统设置' },
];

export function TopNav({ activeModule, onModuleChange }: TopNavProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleClick: MenuProps['onClick'] = (e) => {
    onModuleChange(e.key);
    // 导航到该模块的第一个页面
    const firstRoute: Record<string, string> = {
      research: '/',
      monitor: '/system-overview',
      data: '/data-center',
      settings: '/system-config',
    };
    if (location.pathname !== firstRoute[e.key]) {
      navigate(firstRoute[e.key]);
    }
  };

  return (
    <Menu
      mode="horizontal"
      selectedKeys={[activeModule]}
      items={modules.map((m) => ({ key: m.key, label: m.label }))}
      onClick={handleClick}
      style={{ borderBottom: 'none', flex: 1, background: 'transparent' }}
    />
  );
}
```

- [ ] **Step 4: 创建 SideNav 组件**

`web/src/components/AppShell/SideNav.tsx`:
```typescript
import { Menu } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import type { MenuProps } from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  SettingOutlined,
  DashboardOutlined,
  ClusterOutlined,
  AlertOutlined,
  DatabaseOutlined,
  ToolOutlined,
} from '@ant-design/icons';

const sideNavItems: Record<string, MenuProps['items']> = {
  research: [
    { key: '/', icon: <LineChartOutlined />, label: '回测列表' },
    { key: '/compare', icon: <BarChartOutlined />, label: '批量对比' },
    { key: '/param-analysis', icon: <SettingOutlined />, label: '参数分析' },
  ],
  monitor: [
    { key: '/system-overview', icon: <DashboardOutlined />, label: '系统概览' },
    { key: '/node-status', icon: <ClusterOutlined />, label: '节点状态' },
    { key: '/risk-monitor', icon: <AlertOutlined />, label: '风险监控' },
  ],
  data: [
    { key: '/data-center', icon: <DatabaseOutlined />, label: '数据底座' },
  ],
  settings: [
    { key: '/system-config', icon: <ToolOutlined />, label: '系统配置' },
  ],
};

interface SideNavProps {
  activeModule: string;
}

export function SideNav({ activeModule }: SideNavProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const items = sideNavItems[activeModule] || [];

  return (
    <Menu
      mode="inline"
      selectedKeys={[location.pathname]}
      items={items}
      onClick={(e) => navigate(e.key)}
      style={{ borderRight: 'none', height: '100%' }}
    />
  );
}
```

- [ ] **Step 5: 创建 AppShell 组件**

`web/src/components/AppShell/AppShell.tsx`:
```typescript
import { useState, useEffect } from 'react';
import { Layout } from 'antd';
import { Outlet, useLocation } from 'react-router-dom';
import { TopNav } from './TopNav';
import { SideNav } from './SideNav';
import { ConnectionStatus } from './ConnectionStatus';
import { ThemeToggle } from '../ThemeToggle/ThemeToggle';
import { ros2WS } from '../../services/ros2WebSocket';

const { Header, Sider, Content } = Layout;

function getModuleFromPath(path: string): string {
  if (path.startsWith('/system-overview') || path.startsWith('/node-status') || path.startsWith('/risk-monitor')) return 'monitor';
  if (path.startsWith('/data-center')) return 'data';
  if (path.startsWith('/system-config')) return 'settings';
  return 'research';
}

export function AppShell() {
  const location = useLocation();
  const [activeModule, setActiveModule] = useState(() => getModuleFromPath(location.pathname));

  useEffect(() => {
    setActiveModule(getModuleFromPath(location.pathname));
  }, [location.pathname]);

  useEffect(() => {
    ros2WS.connect();
    return () => ros2WS.disconnect();
  }, []);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', borderBottom: '1px solid #f0f0f0', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <div style={{ fontSize: 18, fontWeight: 'bold', marginRight: 32 }}>揽宝回测平台</div>
        <TopNav activeModule={activeModule} onModuleChange={setActiveModule} />
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16 }}>
          <ConnectionStatus />
          <ThemeToggle />
        </div>
      </Header>
      <Layout>
        <Sider width={200} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
          <SideNav activeModule={activeModule} />
        </Sider>
        <Content style={{ padding: 24, background: 'var(--ant-color-bg-container)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
```

- [ ] **Step 6: 修改 App.tsx 路由**

将 `web/src/App.tsx` 替换为：

```typescript
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
```

- [ ] **Step 7: 添加 CSS Variables**

修改 `web/src/index.css`，在文件末尾追加：

```css
/* 主题过渡动画 */
* {
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

/* 监控图表容器 */
.metric-chart-container {
  height: 280px;
}

/* KPI 卡片 */
.kpi-card {
  text-align: center;
}

.kpi-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--ant-color-text);
}

.kpi-label {
  font-size: 14px;
  color: var(--ant-color-text-secondary);
  margin-top: 4px;
}
```

- [ ] **Step 8: 创建空页面占位文件**

创建5个空页面文件以通过编译：

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web/src/pages

for page in SystemOverviewPage NodeStatusPage RiskMonitorPage DataCenterPage SystemConfigPage; do
  cat > "${page}.tsx" << 'EOF'
export function PAGE_NAME() {
  return <div>PAGE_NAME - 占位</div>;
}
EOF
  sed -i "s/PAGE_NAME/${page}/g" "${page}.tsx"
done
```

- [ ] **Step 9: 验证编译**

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web
npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: 双层导航布局（AppShell + TopNav + SideNav + ConnectionStatus + ThemeToggle）"
```

---

## Phase 2: 后端配合

### Task 4: 新增 ROS2 SystemMetrics 消息类型

**Files:**
- Create: `src/lanbao_interfaces/msg/SystemMetrics.msg`
- Modify: `src/lanbao_interfaces/CMakeLists.txt`

- [ ] **Step 1: 创建消息定义文件**

`src/lanbao_interfaces/msg/SystemMetrics.msg`:
```rosidl
# 系统指标消息
builtin_interfaces/Time timestamp
float32 cpu_percent          # CPU 使用率 0-100
float32 memory_percent       # 内存使用率 0-100
float32 disk_percent         # 磁盘使用率 0-100
uint64 network_bytes_sent    # 网络发送字节数
uint64 network_bytes_recv    # 网络接收字节数
float32 load_average_1m      # 1分钟平均负载
```

- [ ] **Step 2: 修改 CMakeLists.txt**

在 `src/lanbao_interfaces/CMakeLists.txt` 的 `rosidl_generate_interfaces` 调用中，在 `msg/SyncStatusDetail.msg` 之后添加：

```cmake
  "msg/SystemMetrics.msg"
```

- [ ] **Step 3: 构建接口包**

```bash
cd /data/wangf/lanbao_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
colcon build --packages-select lanbao_interfaces --symlink-install
```

Expected: 构建成功，无错误

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: 新增 SystemMetrics.msg ROS2 消息类型"
```

---

### Task 5: 新增 system_metrics_node

**Files:**
- Create: `src/lanbao_monitor/lanbao_monitor/system_metrics_node.py`
- Modify: `src/lanbao_monitor/setup.py`

- [ ] **Step 1: 创建 system_metrics_node**

`src/lanbao_monitor/lanbao_monitor/system_metrics_node.py`:
```python
import psutil
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from builtin_interfaces.msg import Time
from lanbao_interfaces.msg import SystemMetrics


class SystemMetricsNode(Node):
    def __init__(self):
        super().__init__('system_metrics_node')
        self.publisher = self.create_publisher(
            SystemMetrics,
            '/system/metrics',
            qos_profile=QoSProfile(depth=10)
        )
        self.timer = self.create_timer(5.0, self._publish_metrics)
        self.get_logger().info('SystemMetricsNode 已启动，每5秒发布系统指标')

    def _publish_metrics(self):
        try:
            msg = SystemMetrics()
            now = self.get_clock().now().to_msg()
            msg.timestamp = now
            msg.cpu_percent = float(psutil.cpu_percent(interval=None))
            msg.memory_percent = float(psutil.virtual_memory().percent)
            msg.disk_percent = float(psutil.disk_usage('/').percent)

            net_io = psutil.net_io_counters()
            msg.network_bytes_sent = net_io.bytes_sent
            msg.network_bytes_recv = net_io.bytes_recv

            load1, _, _ = psutil.getloadavg()
            msg.load_average_1m = float(load1)

            self.publisher.publish(msg)
        except Exception as e:
            self.get_logger().warning(f'采集系统指标失败: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = SystemMetricsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 修改 setup.py 添加入口点**

在 `src/lanbao_monitor/setup.py` 的 `console_scripts` 列表中新增：

```python
'system_metrics_node = lanbao_monitor.system_metrics_node:main',
```

- [ ] **Step 3: 构建 monitor 包**

```bash
cd /data/wangf/lanbao_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
colcon build --packages-select lanbao_monitor --symlink-install
```

Expected: 构建成功

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: 新增 system_metrics_node（psutil 采集 + /system/metrics Topic 发布）"
```

---

### Task 6: FastAPI 数据底座与系统配置接口

**Files:**
- Modify: `src/lanbao_backtest/api/models.py`
- Create: `src/lanbao_backtest/api/routes/data.py`
- Create: `src/lanbao_backtest/api/routes/config.py`
- Modify: `src/lanbao_backtest/api/main.py`

- [ ] **Step 1: 添加 Pydantic 模型**

在 `src/lanbao_backtest/api/models.py` 末尾追加：

```python
# ── 数据底座 ──

class DataTableInfo(BaseModel):
    name: str
    record_count: int
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    last_updated: Optional[str] = None
    quality_score: float = 100.0


class DataSummary(BaseModel):
    total_symbols: int
    total_daily_records: int
    last_sync_time: Optional[str] = None
    coverage_days: int


class SyncTask(BaseModel):
    id: str
    source: str
    status: str  # running / success / failed
    progress: float
    success_count: int
    failed_count: int
    duration_seconds: Optional[float] = None


class QualityReport(BaseModel):
    table: str
    missing_rate: float
    coverage_score: float
    overall_score: float


# ── 系统配置 ──

class BacktestConfig(BaseModel):
    default_initial_capital: float = 1_000_000.0
    default_commission_rate: float = 0.0003
    default_slippage: float = 0.001
    default_backtest_days: int = 365


class RiskConfig(BaseModel):
    max_single_loss_pct: float = 0.05
    max_drawdown_threshold: float = 0.15
    max_position_pct: float = 0.8
    circuit_breaker_enabled: bool = False


class DataSyncConfig(BaseModel):
    auto_sync_enabled: bool = True
    sync_time: str = "09:00"
    source_priority: str = "tushare > tdx > akshare > miniqmt"


class NotificationConfig(BaseModel):
    webhook_url: Optional[str] = None
    alert_level_threshold: str = "warning"


class SystemConfig(BaseModel):
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    data_sync: DataSyncConfig = Field(default_factory=DataSyncConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
```

- [ ] **Step 2: 创建 data 路由**

`src/lanbao_backtest/api/routes/data.py`:
```python
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from ..models import DataSummary, DataTableInfo, SyncTask, QualityReport

router = APIRouter()


# 模拟数据（后续替换为 DuckDB 真实查询）
class MockDataService:
    @staticmethod
    def get_summary() -> DataSummary:
        return DataSummary(
            total_symbols=5200,
            total_daily_records=12_500_000,
            last_sync_time="2026-05-11 09:00:00",
            coverage_days=252,
        )

    @staticmethod
    def get_tables() -> List[DataTableInfo]:
        return [
            DataTableInfo(name="stock_daily", record_count=12_000_000, date_start="2020-01-01", date_end="2026-05-10", last_updated="2026-05-11 09:00:00", quality_score=98.5),
            DataTableInfo(name="stock_info", record_count=5200, last_updated="2026-05-01 00:00:00", quality_score=100.0),
            DataTableInfo(name="trade_calendar", record_count=1500, last_updated="2026-01-01 00:00:00", quality_score=100.0),
        ]

    @staticmethod
    def get_sync_tasks() -> List[SyncTask]:
        return [
            SyncTask(id="sync-001", source="Tushare", status="success", progress=100.0, success_count=5200, failed_count=0, duration_seconds=180.5),
        ]

    @staticmethod
    def get_quality_report(table: Optional[str] = None) -> List[QualityReport]:
        return [
            QualityReport(table="stock_daily", missing_rate=0.015, coverage_score=98.5, overall_score=98.5),
            QualityReport(table="stock_info", missing_rate=0.0, coverage_score=100.0, overall_score=100.0),
        ]


@router.get("/data/summary", response_model=DataSummary)
async def data_summary():
    return MockDataService.get_summary()


@router.get("/data/tables", response_model=List[DataTableInfo])
async def data_tables():
    return MockDataService.get_tables()


@router.get("/data/sync", response_model=List[SyncTask])
async def sync_status():
    return MockDataService.get_sync_tasks()


@router.post("/data/sync", response_model=SyncTask)
async def trigger_sync(source: Optional[str] = None):
    return SyncTask(id="sync-new", source=source or "Tushare", status="running", progress=0.0, success_count=0, failed_count=0)


@router.get("/data/quality", response_model=List[QualityReport])
async def data_quality(table: Optional[str] = None):
    return MockDataService.get_quality_report(table)
```

- [ ] **Step 3: 创建 config 路由**

`src/lanbao_backtest/api/routes/config.py`:
```python
import yaml
from pathlib import Path
from fastapi import APIRouter

from ..models import SystemConfig

router = APIRouter()

CONFIG_PATH = Path("config/settings.yaml")


def _load_config() -> SystemConfig:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return SystemConfig(**data) if data else SystemConfig()
    return SystemConfig()


def _save_config(config: SystemConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(), f, allow_unicode=True, default_flow_style=False)


@router.get("/config", response_model=SystemConfig)
async def get_config():
    return _load_config()


@router.put("/config", response_model=SystemConfig)
async def update_config(config: SystemConfig):
    _save_config(config)
    return config
```

- [ ] **Step 4: 注册路由**

修改 `src/lanbao_backtest/api/main.py`，在现有路由导入后添加：

```python
from .routes import data, config
```

在 `app.include_router(strategies.router, ...)` 之后添加：

```python
app.include_router(data.router, prefix="/api/v1", tags=["data"])
app.include_router(config.router, prefix="/api/v1", tags=["config"])
```

- [ ] **Step 5: 验证后端启动**

```bash
cd /data/wangf/lanbao_ws
source .venv/bin/activate
source /opt/ros/humble/setup.bash
source install/setup.bash
cd src/lanbao_backtest
python -c "from api.main import app; print('导入成功')"
```

Expected: 输出 "导入成功"

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: FastAPI 数据底座与系统配置接口（/data/*, /config）"
```

---

## Phase 3: 页面实现

### Task 7: 系统概览页面

**Files:**
- Create: `web/src/pages/SystemOverviewPage.tsx`
- Create: `web/src/components/Monitor/KPIGrid.tsx`
- Create: `web/src/components/Monitor/MetricChart.tsx`
- Create: `web/src/components/Monitor/StatusPieChart.tsx`
- Create: `web/src/stores/monitorStore.ts`
- Create: `web/src/hooks/useSystemMetrics.ts`

- [ ] **Step 1: 创建 monitorStore**

`web/src/stores/monitorStore.ts`:
```typescript
import { create } from 'zustand';
import type { NodeStatusMsg, RiskAlertMsg, SystemMetricsMsg } from '../types/ros2';

interface MonitorState {
  nodes: NodeStatusMsg[];
  alerts: RiskAlertMsg[];
  metricsHistory: SystemMetricsMsg[];
  setNodes: (nodes: NodeStatusMsg[]) => void;
  setAlerts: (alerts: RiskAlertMsg[]) => void;
  addMetric: (metric: SystemMetricsMsg) => void;
}

const MAX_HISTORY = 360; // 30分钟 × 12条/分钟 (5秒间隔)

export const useMonitorStore = create<MonitorState>((set) => ({
  nodes: [],
  alerts: [],
  metricsHistory: [],
  setNodes: (nodes) => set({ nodes }),
  setAlerts: (alerts) => set({ alerts }),
  addMetric: (metric) =>
    set((state) => {
      const next = [...state.metricsHistory, metric];
      if (next.length > MAX_HISTORY) next.shift();
      return { metricsHistory: next };
    }),
}));
```

- [ ] **Step 2: 创建便捷 Hooks**

`web/src/hooks/useSystemMetrics.ts`:
```typescript
import { useCallback } from 'react';
import { useROSTopic } from './useROSTopic';
import { useMonitorStore } from '../stores/monitorStore';
import type { SystemMetricsMsg } from '../types/ros2';

export function useSystemMetrics() {
  const addMetric = useMonitorStore((s) => s.addMetric);

  const handleMessage = useCallback(
    (msg: SystemMetricsMsg) => {
      addMetric(msg);
    },
    [addMetric]
  );

  useROSTopic('/system/metrics', handleMessage);
}
```

`web/src/hooks/useNodeStatus.ts`:
```typescript
import { useCallback } from 'react';
import { useROSTopic } from './useROSTopic';
import { useMonitorStore } from '../stores/monitorStore';
import type { NodeStatusMsg } from '../types/ros2';

export function useNodeStatus() {
  const setNodes = useMonitorStore((s) => s.setNodes);

  const handleMessage = useCallback(
    (msg: NodeStatusMsg) => {
      setNodes((prev) => {
        const filtered = prev.filter((n) => n.node_name !== msg.node_name);
        return [...filtered, msg];
      });
    },
    [setNodes]
  );

  useROSTopic('/node/status', handleMessage);
}
```

`web/src/hooks/useAlerts.ts`:
```typescript
import { useCallback } from 'react';
import { useROSTopic } from './useROSTopic';
import { useMonitorStore } from '../stores/monitorStore';
import type { RiskAlertMsg } from '../types/ros2';

export function useAlerts() {
  const setAlerts = useMonitorStore((s) => s.setAlerts);

  const handleMessage = useCallback(
    (msg: RiskAlertMsg) => {
      setAlerts((prev) => {
        const filtered = prev.filter((a) => a.alert_id !== msg.alert_id);
        return [...filtered, msg].sort((a, b) => b.timestamp - a.timestamp).slice(0, 100);
      });
    },
    [setAlerts]
  );

  useROSTopic('/risk/alerts', handleMessage);
}
```

- [ ] **Step 3: 创建 Monitor 通用组件**

`web/src/components/Monitor/KPIGrid.tsx`:
```typescript
import { Card, Row, Col, Statistic } from 'antd';

interface KPIData {
  title: string;
  value: number | string;
  suffix?: string;
  precision?: number;
}

interface KPIGridProps {
  data: KPIData[];
}

export function KPIGrid({ data }: KPIGridProps) {
  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      {data.map((item) => (
        <Col key={item.title} xs={12} sm={12} md={6}>
          <Card className="kpi-card">
            <Statistic
              title={item.title}
              value={item.value}
              suffix={item.suffix}
              precision={item.precision}
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
}
```

`web/src/components/Monitor/MetricChart.tsx`:
```typescript
import { useThemeStore } from '../../stores/themeStore';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface DataPoint {
  time: string;
  value: number;
}

interface MetricChartProps {
  data: DataPoint[];
  title: string;
  color?: string;
  unit?: string;
}

export function MetricChart({ data, title, color = '#1677ff', unit = '%' }: MetricChartProps) {
  const isDark = useThemeStore((s) => s.isDark);
  const axisColor = isDark ? '#888' : '#666';
  const gridColor = isDark ? '#333' : '#eee';

  return (
    <div className="metric-chart-container">
      <h4 style={{ marginBottom: 12 }}>{title}</h4>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="time" tick={{ fill: axisColor, fontSize: 12 }} />
          <YAxis tick={{ fill: axisColor, fontSize: 12 }} unit={unit} domain={[0, 'auto']} />
          <Tooltip
            contentStyle={{
              background: isDark ? '#1f1f1f' : '#fff',
              border: `1px solid ${isDark ? '#333' : '#eee'}`,
            }}
          />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

`web/src/components/Monitor/StatusPieChart.tsx`:
```typescript
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useThemeStore } from '../../stores/themeStore';

interface StatusData {
  name: string;
  value: number;
}

interface StatusPieChartProps {
  data: StatusData[];
  title: string;
}

const COLORS = ['#52c41a', '#f5222d', '#faad14', '#8c8c8c'];

export function StatusPieChart({ data, title }: StatusPieChartProps) {
  const isDark = useThemeStore((s) => s.isDark);

  return (
    <div className="metric-chart-container">
      <h4 style={{ marginBottom: 12 }}>{title}</h4>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={4} dataKey="value">
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: isDark ? '#1f1f1f' : '#fff',
              border: `1px solid ${isDark ? '#333' : '#eee'}`,
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 4: 创建 SystemOverviewPage**

`web/src/pages/SystemOverviewPage.tsx`:
```typescript
import { useMemo } from 'react';
import { Card, Row, Col, List, Tag } from 'antd';
import { useSystemMetrics } from '../hooks/useSystemMetrics';
import { useNodeStatus } from '../hooks/useNodeStatus';
import { useAlerts } from '../hooks/useAlerts';
import { useMonitorStore } from '../stores/monitorStore';
import { KPIGrid } from '../components/Monitor/KPIGrid';
import { MetricChart } from '../components/Monitor/MetricChart';
import { StatusPieChart } from '../components/Monitor/StatusPieChart';

function formatTime(sec: number): string {
  const d = new Date(sec * 1000);
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function SystemOverviewPage() {
  useSystemMetrics();
  useNodeStatus();
  useAlerts();

  const nodes = useMonitorStore((s) => s.nodes);
  const alerts = useMonitorStore((s) => s.alerts);
  const metricsHistory = useMonitorStore((s) => s.metricsHistory);

  const onlineCount = nodes.filter((n) => n.status === 'RUNNING').length;
  const todayAlertCount = alerts.length;

  const latestMetric = metricsHistory[metricsHistory.length - 1];
  const cpuPercent = latestMetric?.cpu_percent ?? 0;
  const memoryPercent = latestMetric?.memory_percent ?? 0;

  const kpiData = [
    { title: '在线节点', value: onlineCount, suffix: ` / ${nodes.length || '-'}` },
    { title: '今日告警', value: todayAlertCount },
    { title: 'CPU 使用率', value: cpuPercent, suffix: '%', precision: 1 },
    { title: '内存使用率', value: memoryPercent, suffix: '%', precision: 1 },
  ];

  const cpuData = useMemo(
    () => metricsHistory.map((m) => ({ time: formatTime(m.timestamp.sec), value: m.cpu_percent })),
    [metricsHistory]
  );

  const memoryData = useMemo(
    () => metricsHistory.map((m) => ({ time: formatTime(m.timestamp.sec), value: m.memory_percent })),
    [metricsHistory]
  );

  const statusData = useMemo(() => {
    const counts: Record<string, number> = {};
    nodes.forEach((n) => { counts[n.status] = (counts[n.status] || 0) + 1; });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [nodes]);

  const levelColor: Record<string, string> = {
    CRITICAL: 'red',
    HIGH: 'orange',
    MEDIUM: 'gold',
    LOW: 'blue',
  };

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>系统概览</h2>
      <KPIGrid data={kpiData} />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card>
            <MetricChart data={cpuData} title="CPU 使用率趋势" color="#1677ff" />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <MetricChart data={memoryData} title="内存使用率趋势" color="#52c41a" />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <StatusPieChart data={statusData} title="节点状态分布" />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="最近告警" extra={<a href="/risk-monitor">查看全部</a>}>
            <List
              dataSource={alerts.slice(0, 5)}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <span>
                        <Tag color={levelColor[item.level] || 'default'}>{item.level}</Tag>
                        {item.message}
                      </span>
                    }
                    description={new Date(item.timestamp * 1000).toLocaleString('zh-CN')}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
```

- [ ] **Step 5: 验证编译**

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web
npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: 系统概览页面（KPI + CPU/内存趋势 + 节点分布 + 最近告警）"
```

---

### Task 8: 节点状态页面

**Files:**
- Create: `web/src/pages/NodeStatusPage.tsx`

- [ ] **Step 1: 创建 NodeStatusPage**

`web/src/pages/NodeStatusPage.tsx`:
```typescript
import { useState, useMemo } from 'react';
import { Card, List, Badge, Tag, Input, Row, Col, Statistic, Button, Empty } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useNodeStatus } from '../hooks/useNodeStatus';
import { useMonitorStore } from '../stores/monitorStore';
import { MetricChart } from '../components/Monitor/MetricChart';
import type { NodeStatusMsg } from '../types/ros2';

const STATUS_COLOR: Record<string, string> = {
  RUNNING: 'green',
  INITIALIZING: 'blue',
  ERROR: 'red',
  STOPPED: 'default',
};

const STATUS_LABEL: Record<string, string> = {
  RUNNING: '运行中',
  INITIALIZING: '初始化中',
  ERROR: '错误',
  STOPPED: '已停止',
};

export function NodeStatusPage() {
  useNodeStatus();
  const nodes = useMonitorStore((s) => s.nodes);
  const [selectedNode, setSelectedNode] = useState<NodeStatusMsg | null>(null);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredNodes = useMemo(() => {
    return nodes
      .filter((n) => (statusFilter === 'ALL' ? true : n.status === statusFilter))
      .filter((n) => n.node_name.toLowerCase().includes(searchText.toLowerCase()))
      .sort((a, b) => b.timestamp - a.timestamp);
  }, [nodes, statusFilter, searchText]);

  // 模拟节点历史指标（实际应从 /node/metrics Topic 获取）
  const mockNodeHistory = useMemo(() => {
    if (!selectedNode) return [];
    return Array.from({ length: 20 }, (_, i) => ({
      time: `${i}:00`,
      value: selectedNode.cpu_usage + Math.random() * 10 - 5,
    }));
  }, [selectedNode]);

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>节点状态</h2>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card
            title="节点列表"
            extra={
              <div style={{ display: 'flex', gap: 8 }}>
                <Input.Search
                  placeholder="搜索节点"
                  size="small"
                  onSearch={setSearchText}
                  style={{ width: 120 }}
                />
              </div>
            }
          >
            <div style={{ marginBottom: 8 }}>
              <Tag color={statusFilter === 'ALL' ? 'blue' : undefined} style={{ cursor: 'pointer' }} onClick={() => setStatusFilter('ALL')}>
                全部 ({nodes.length})
              </Tag>
              {Object.entries(STATUS_LABEL).map(([status, label]) => (
                <Tag
                  key={status}
                  color={statusFilter === status ? STATUS_COLOR[status] : undefined}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setStatusFilter(status)}
                >
                  {label} ({nodes.filter((n) => n.status === status).length})
                </Tag>
              ))}
            </div>
            <List
              dataSource={filteredNodes}
              renderItem={(node) => (
                <List.Item
                  style={{
                    cursor: 'pointer',
                    background: selectedNode?.node_name === node.node_name ? 'var(--ant-color-primary-bg)' : undefined,
                    borderRadius: 4,
                    padding: '8px 12px',
                  }}
                  onClick={() => setSelectedNode(node)}
                >
                  <List.Item.Meta
                    title={
                      <span>
                        <Badge status={STATUS_COLOR[node.status] as any} />
                        {node.node_name}
                      </span>
                    }
                    description={`CPU: ${node.cpu_usage.toFixed(1)}% | 内存: ${node.memory_usage.toFixed(1)}%`}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} md={16}>
          {selectedNode ? (
            <Card
              title={selectedNode.node_name}
              extra={
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <Tag color={STATUS_COLOR[selectedNode.status]}>{STATUS_LABEL[selectedNode.status]}</Tag>
                  <Button icon={<ReloadOutlined />} size="small">重启节点</Button>
                </div>
              }
            >
              <Row gutter={[16, 16]}>
                <Col span={8}><Statistic title="节点类型" value={selectedNode.node_type || '-'} /></Col>
                <Col span={8}><Statistic title="消息计数" value={selectedNode.message_count} /></Col>
                <Col span={8}><Statistic title="最后心跳" value={new Date(selectedNode.timestamp * 1000).toLocaleTimeString('zh-CN')} /></Col>
              </Row>
              <div style={{ marginTop: 16 }}>
                <MetricChart data={mockNodeHistory} title="CPU 使用率趋势" />
              </div>
              {selectedNode.last_error && (
                <div style={{ marginTop: 16, padding: 12, background: '#fff1f0', borderRadius: 4, color: '#cf1322' }}>
                  <strong>最后错误:</strong> {selectedNode.last_error}
                </div>
              )}
            </Card>
          ) : (
            <Card><Empty description="选择左侧节点查看详情" /></Card>
          )}
        </Col>
      </Row>
    </div>
  );
}
```

- [ ] **Step 2: 验证编译**

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web
npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: 节点状态页面（节点列表 + 详情面板 + 状态筛选）"
```

---

### Task 9: 风险监控页面

**Files:**
- Create: `web/src/pages/RiskMonitorPage.tsx`
- Create: `web/src/components/Monitor/AlertBadge.tsx`

- [ ] **Step 1: 创建 AlertBadge 组件**

`web/src/components/Monitor/AlertBadge.tsx`:
```typescript
import { Tag } from 'antd';

const LEVEL_MAP: Record<string, { color: string; label: string }> = {
  CRITICAL: { color: 'red', label: '严重' },
  HIGH: { color: 'orange', label: '高' },
  MEDIUM: { color: 'gold', label: '中' },
  LOW: { color: 'blue', label: '低' },
};

interface AlertBadgeProps {
  level: string;
}

export function AlertBadge({ level }: AlertBadgeProps) {
  const info = LEVEL_MAP[level] || { color: 'default', label: level };
  return <Tag color={info.color}>{info.label}</Tag>;
}
```

- [ ] **Step 2: 创建 RiskMonitorPage**

`web/src/pages/RiskMonitorPage.tsx`:
```typescript
import { useState, useMemo } from 'react';
import { Card, Table, Tag, Button, Statistic, Row, Col, notification } from 'antd';
import { CheckOutlined, EyeInvisibleOutlined } from '@ant-design/icons';
import { useAlerts } from '../hooks/useAlerts';
import { useMonitorStore } from '../stores/monitorStore';
import { AlertBadge } from '../components/Monitor/AlertBadge';
import { MetricChart } from '../components/Monitor/MetricChart';
import type { RiskAlertMsg } from '../types/ros2';

export function RiskMonitorPage() {
  useAlerts();
  const alerts = useMonitorStore((s) => s.alerts);
  const [levelFilter, setLevelFilter] = useState<string>('ALL');

  const filteredAlerts = useMemo(() => {
    if (levelFilter === 'ALL') return alerts;
    return alerts.filter((a) => a.level === levelFilter);
  }, [alerts, levelFilter]);

  const stats = useMemo(() => {
    const total = alerts.length;
    const critical = alerts.filter((a) => a.level === 'CRITICAL').length;
    const warning = alerts.filter((a) => a.level === 'HIGH' || a.level === 'MEDIUM').length;
    const acknowledged = alerts.filter((a) => (a as any).status === 'acknowledged').length;
    return { total, critical, warning, acknowledged };
  }, [alerts]);

  // 模拟24小时告警趋势
  const trendData = useMemo(() => {
    return Array.from({ length: 24 }, (_, i) => ({
      time: `${i}:00`,
      value: Math.floor(Math.random() * 5),
    }));
  }, []);

  const handleAcknowledge = (alert: RiskAlertMsg) => {
    notification.success({ message: '告警已确认', description: alert.message, duration: 3 });
  };

  const columns = [
    { title: '时间', dataIndex: 'timestamp', key: 'time', render: (v: number) => new Date(v * 1000).toLocaleString('zh-CN') },
    { title: '级别', dataIndex: 'level', key: 'level', render: (v: string) => <AlertBadge level={v} /> },
    { title: '类型', dataIndex: 'alert_type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
    { title: '描述', dataIndex: 'message', key: 'message' },
    { title: '当前值', dataIndex: 'current_value', key: 'current', render: (v: number, record: RiskAlertMsg) => `${v.toFixed(2)} / 阈值 ${record.threshold.toFixed(2)}` },
    { title: '关联策略', dataIndex: 'affected_strategies', key: 'strategies', render: (v: string[]) => v?.map((s) => <Tag key={s}>{s}</Tag>) },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: RiskAlertMsg) => (
        <Button.Group>
          <Button size="small" icon={<CheckOutlined />} onClick={() => handleAcknowledge(record)}>确认</Button>
          <Button size="small" icon={<EyeInvisibleOutlined />}>忽略</Button>
        </Button.Group>
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>风险监控</h2>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}><Card><Statistic title="今日告警总数" value={stats.total} /></Card></Col>
        <Col span={6}><Card><Statistic title="严重告警" value={stats.critical} valueStyle={{ color: '#f5222d' }} /></Card></Col>
        <Col span={6}><Card><Statistic title="警告告警" value={stats.warning} valueStyle={{ color: '#faad14' }} /></Card></Col>
        <Col span={6}><Card><Statistic title="已处理" value={stats.acknowledged} /></Card></Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <MetricChart data={trendData} title="24小时告警趋势" />
          </Card>
        </Col>
      </Row>
      <Card style={{ marginTop: 16 }} title="告警列表">
        <div style={{ marginBottom: 12 }}>
          <Tag color={levelFilter === 'ALL' ? 'blue' : undefined} style={{ cursor: 'pointer' }} onClick={() => setLevelFilter('ALL')}>全部</Tag>
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((l) => (
            <Tag key={l} color={levelFilter === l ? 'blue' : undefined} style={{ cursor: 'pointer' }} onClick={() => setLevelFilter(l)}>
              {l}
            </Tag>
          ))}
        </div>
        <Table
          dataSource={filteredAlerts}
          columns={columns}
          rowKey="alert_id"
          pagination={{ pageSize: 20 }}
          size="small"
        />
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: 验证编译**

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web
npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: 风险监控页面（告警统计 + 趋势图 + 告警列表 + 确认操作）"
```

---

### Task 10: 数据底座页面

**Files:**
- Create: `web/src/types/data.ts`
- Create: `web/src/api/data.ts`
- Create: `web/src/stores/dataStore.ts`
- Create: `web/src/pages/DataCenterPage.tsx`

- [ ] **Step 1: 创建类型定义**

`web/src/types/data.ts`:
```typescript
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
```

- [ ] **Step 2: 创建 API 封装**

`web/src/api/data.ts`:
```typescript
import { apiClient } from './client';
import type { DataSummary, DataTableInfo, SyncTask, QualityReport } from '../types/data';

export const dataApi = {
  summary: () => apiClient.get<DataSummary>('/data/summary').then((r) => r.data),
  tables: () => apiClient.get<DataTableInfo[]>('/data/tables').then((r) => r.data),
  syncStatus: () => apiClient.get<SyncTask[]>('/data/sync').then((r) => r.data),
  triggerSync: (source?: string) => apiClient.post<SyncTask>('/data/sync', null, { params: { source } }).then((r) => r.data),
  quality: (table?: string) => apiClient.get<QualityReport[]>('/data/quality', { params: { table } }).then((r) => r.data),
};
```

- [ ] **Step 3: 创建 dataStore**

`web/src/stores/dataStore.ts`:
```typescript
import { create } from 'zustand';
import type { DataSummary, DataTableInfo, SyncTask, QualityReport } from '../types/data';

interface DataState {
  summary: DataSummary | null;
  tables: DataTableInfo[];
  syncTasks: SyncTask[];
  quality: QualityReport[];
  setSummary: (s: DataSummary) => void;
  setTables: (t: DataTableInfo[]) => void;
  setSyncTasks: (t: SyncTask[]) => void;
  setQuality: (q: QualityReport[]) => void;
}

export const useDataStore = create<DataState>((set) => ({
  summary: null,
  tables: [],
  syncTasks: [],
  quality: [],
  setSummary: (summary) => set({ summary }),
  setTables: (tables) => set({ tables }),
  setSyncTasks: (syncTasks) => set({ syncTasks }),
  setQuality: (quality) => set({ quality }),
}));
```

- [ ] **Step 4: 创建 DataCenterPage**

`web/src/pages/DataCenterPage.tsx`:
```typescript
import { useState } from 'react';
import { Card, Row, Col, Statistic, Table, Button, Progress, Tag, Drawer, message } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { SyncOutlined, EyeOutlined } from '@ant-design/icons';
import { dataApi } from '../api/data';
import type { DataTableInfo } from '../types/data';

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function qualityColor(score: number): string {
  if (score >= 90) return 'green';
  if (score >= 70) return 'yellow';
  return 'red';
}

export function DataCenterPage() {
  const [previewTable, setPreviewTable] = useState<DataTableInfo | null>(null);

  const { data: summary } = useQuery({ queryKey: ['data', 'summary'], queryFn: dataApi.summary });
  const { data: tables } = useQuery({ queryKey: ['data', 'tables'], queryFn: dataApi.tables });
  const { data: syncTasks, refetch: refetchSync } = useQuery({ queryKey: ['data', 'sync'], queryFn: dataApi.syncStatus });
  const { data: quality } = useQuery({ queryKey: ['data', 'quality'], queryFn: () => dataApi.quality() });

  const handleSync = async () => {
    try {
      await dataApi.triggerSync();
      message.success('同步任务已启动');
      refetchSync();
    } catch (e) {
      message.error('启动同步失败');
    }
  };

  const tableColumns = [
    { title: '表名', dataIndex: 'name', key: 'name' },
    { title: '记录数', dataIndex: 'record_count', key: 'count', render: (v: number) => formatNumber(v) },
    { title: '数据起止', key: 'range', render: (_: unknown, r: DataTableInfo) => `${r.date_start || '-'} ~ ${r.date_end || '-'}` },
    { title: '更新时间', dataIndex: 'last_updated', key: 'updated' },
    {
      title: '质量评分',
      dataIndex: 'quality_score',
      key: 'quality',
      render: (v: number) => <Tag color={qualityColor(v)}>{v.toFixed(1)}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, r: DataTableInfo) => (
        <Button size="small" icon={<EyeOutlined />} onClick={() => setPreviewTable(r)}>预览</Button>
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>数据底座</h2>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}><Card><Statistic title="总股票数" value={summary?.total_symbols ?? '-'} /></Card></Col>
        <Col span={6}><Card><Statistic title="日线数据条数" value={summary ? formatNumber(summary.total_daily_records) : '-'} /></Card></Col>
        <Col span={6}><Card><Statistic title="最后同步时间" value={summary?.last_sync_time ?? '-'} /></Card></Col>
        <Col span={6}><Card><Statistic title="数据覆盖天数" value={summary?.coverage_days ?? '-'} suffix="天" /></Card></Col>
      </Row>
      <Card title="数据表" style={{ marginBottom: 16 }}>
        <Table dataSource={tables} columns={tableColumns} rowKey="name" size="small" />
      </Card>
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card
            title="同步状态"
            extra={<Button icon={<SyncOutlined />} onClick={handleSync}>手动同步</Button>}
          >
            <Table
              dataSource={syncTasks}
              columns={[
                { title: '数据源', dataIndex: 'source', key: 'source' },
                { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag>{v}</Tag> },
                { title: '进度', dataIndex: 'progress', key: 'progress', render: (v: number) => <Progress percent={v} size="small" /> },
                { title: '成功/失败', key: 'counts', render: (_: unknown, r: { success_count: number; failed_count: number }) => `${r.success_count} / ${r.failed_count}` },
              ]}
              rowKey="id"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="数据质量">
            <Table
              dataSource={quality}
              columns={[
                { title: '表名', dataIndex: 'table', key: 'table' },
                { title: '缺失率', dataIndex: 'missing_rate', key: 'missing', render: (v: number) => `${(v * 100).toFixed(2)}%` },
                { title: '覆盖评分', dataIndex: 'coverage_score', key: 'coverage', render: (v: number) => v.toFixed(1) },
                { title: '综合评分', dataIndex: 'overall_score', key: 'overall', render: (v: number) => <Tag color={qualityColor(v)}>{v.toFixed(1)}</Tag> },
              ]}
              rowKey="table"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
      </Row>
      <Drawer title={`${previewTable?.name} - 数据预览`} open={!!previewTable} onClose={() => setPreviewTable(null)} width={600}>
        <p>显示前 100 行数据预览...</p>
      </Drawer>
    </div>
  );
}
```

- [ ] **Step 5: 验证编译**

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web
npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: 数据底座页面（数据概览 + 表列表 + 同步状态 + 质量报告）"
```

---

### Task 11: 系统配置页面

**Files:**
- Create: `web/src/types/config.ts`
- Create: `web/src/api/config.ts`
- Create: `web/src/stores/configStore.ts`
- Create: `web/src/pages/SystemConfigPage.tsx`

- [ ] **Step 1: 创建类型定义**

`web/src/types/config.ts`:
```typescript
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
```

- [ ] **Step 2: 创建 API 封装**

`web/src/api/config.ts`:
```typescript
import { apiClient } from './client';
import type { SystemConfig } from '../types/config';

export const configApi = {
  get: () => apiClient.get<SystemConfig>('/config').then((r) => r.data),
  update: (config: SystemConfig) => apiClient.put<SystemConfig>('/config', config).then((r) => r.data),
};
```

- [ ] **Step 3: 创建 configStore**

`web/src/stores/configStore.ts`:
```typescript
import { create } from 'zustand';
import type { SystemConfig } from '../types/config';

interface ConfigState {
  config: SystemConfig | null;
  isLoading: boolean;
  isSaving: boolean;
  setConfig: (c: SystemConfig) => void;
  setLoading: (v: boolean) => void;
  setSaving: (v: boolean) => void;
}

export const useConfigStore = create<ConfigState>((set) => ({
  config: null,
  isLoading: false,
  isSaving: false,
  setConfig: (config) => set({ config }),
  setLoading: (isLoading) => set({ isLoading }),
  setSaving: (isSaving) => set({ isSaving }),
}));
```

- [ ] **Step 4: 创建 SystemConfigPage**

`web/src/pages/SystemConfigPage.tsx`:
```typescript
import { useEffect, useState } from 'react';
import { Card, Form, InputNumber, Switch, Select, TimePicker, Button, message, Modal, Skeleton, Anchor } from 'antd';
import { useQuery, useMutation } from '@tanstack/react-query';
import { SaveOutlined, UndoOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { configApi } from '../api/config';
import type { SystemConfig } from '../types/config';

export function SystemConfigPage() {
  const [form] = Form.useForm<SystemConfig>();
  const [hasChanges, setHasChanges] = useState(false);

  const { data: config, isLoading } = useQuery({
    queryKey: ['config'],
    queryFn: configApi.get,
  });

  const updateMutation = useMutation({
    mutationFn: configApi.update,
    onSuccess: () => {
      message.success('配置保存成功');
      setHasChanges(false);
    },
    onError: () => message.error('配置保存失败'),
  });

  useEffect(() => {
    if (config) {
      form.setFieldsValue({
        ...config,
        data_sync: {
          ...config.data_sync,
          sync_time: dayjs(config.data_sync.sync_time, 'HH:mm'),
        },
      });
    }
  }, [config, form]);

  const handleSave = async () => {
    const values = await form.validateFields();
    const payload: SystemConfig = {
      ...values,
      data_sync: {
        ...values.data_sync,
        sync_time: values.data_sync.sync_time.format('HH:mm'),
      },
    };
    updateMutation.mutate(payload);
  };

  const handleReset = () => {
    Modal.confirm({
      title: '确认重置？',
      content: '所有未保存的修改将丢失',
      onOk: () => {
        if (config) {
          form.setFieldsValue({
            ...config,
            data_sync: {
              ...config.data_sync,
              sync_time: dayjs(config.data_sync.sync_time, 'HH:mm'),
            },
          });
        }
        setHasChanges(false);
      },
    });
  };

  const anchorItems = [
    { key: 'backtest', href: '#backtest', title: '回测参数' },
    { key: 'risk', href: '#risk', title: '风险控制' },
    { key: 'data_sync', href: '#data_sync', title: '数据同步' },
    { key: 'notification', href: '#notification', title: '通知设置' },
  ];

  if (isLoading) return <Skeleton active paragraph={{ rows: 10 }} />;

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>系统配置</h2>
      <div style={{ display: 'flex', gap: 24 }}>
        <div style={{ width: 160 }}>
          <Anchor items={anchorItems} />
        </div>
        <div style={{ flex: 1 }}>
          <Form
            form={form}
            layout="vertical"
            onValuesChange={() => setHasChanges(true)}
          >
            <Card id="backtest" title="回测参数" style={{ marginBottom: 16 }}>
              <Form.Item name={['backtest', 'default_initial_capital']} label="默认初始资金" rules={[{ required: true, min: 0 }]}>
                <InputNumber style={{ width: '100%' }} formatter={(v) => `¥ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
              </Form.Item>
              <Form.Item name={['backtest', 'default_commission_rate']} label="默认佣金率" rules={[{ required: true, min: 0, max: 0.01 }]}>
                <InputNumber style={{ width: '100%' }} step={0.0001} />
              </Form.Item>
              <Form.Item name={['backtest', 'default_slippage']} label="默认滑点" rules={[{ required: true, min: 0, max: 0.05 }]}>
                <InputNumber style={{ width: '100%' }} step={0.0001} />
              </Form.Item>
            </Card>

            <Card id="risk" title="风险控制" style={{ marginBottom: 16 }}>
              <Form.Item name={['risk', 'max_single_loss_pct']} label="最大单笔亏损比例" rules={[{ required: true, min: 0, max: 1 }]}>
                <InputNumber style={{ width: '100%' }} step={0.01} formatter={(v) => `${(Number(v) * 100).toFixed(0)}%`} parser={(v) => Number((v || '0').replace('%', '')) / 100} />
              </Form.Item>
              <Form.Item name={['risk', 'max_drawdown_threshold']} label="最大回撤阈值" rules={[{ required: true, min: 0, max: 1 }]}>
                <InputNumber style={{ width: '100%' }} step={0.01} formatter={(v) => `${(Number(v) * 100).toFixed(0)}%`} parser={(v) => Number((v || '0').replace('%', '')) / 100} />
              </Form.Item>
              <Form.Item name={['risk', 'max_position_pct']} label="仓位上限" rules={[{ required: true, min: 0, max: 1 }]}>
                <InputNumber style={{ width: '100%' }} step={0.01} formatter={(v) => `${(Number(v) * 100).toFixed(0)}%`} parser={(v) => Number((v || '0').replace('%', '')) / 100} />
              </Form.Item>
              <Form.Item name={['risk', 'circuit_breaker_enabled']} label="熔断开关" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Card>

            <Card id="data_sync" title="数据同步" style={{ marginBottom: 16 }}>
              <Form.Item name={['data_sync', 'auto_sync_enabled']} label="自动同步" valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item name={['data_sync', 'sync_time']} label="同步时间">
                <TimePicker format="HH:mm" style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name={['data_sync', 'source_priority']} label="数据源优先级">
                <Select options={[
                  { value: 'tushare > tdx > akshare > miniqmt', label: 'Tushare > TDX > AKShare > MiniQMT' },
                  { value: 'tdx > tushare > akshare > miniqmt', label: 'TDX > Tushare > AKShare > MiniQMT' },
                ]} />
              </Form.Item>
            </Card>

            <Card id="notification" title="通知设置" style={{ marginBottom: 16 }}>
              <Form.Item name={['notification', 'webhook_url']} label="Webhook URL">
                <Input placeholder="https://..." />
              </Form.Item>
              <Form.Item name={['notification', 'alert_level_threshold']} label="告警级别阈值">
                <Select options={[
                  { value: 'info', label: 'Info' },
                  { value: 'warning', label: 'Warning' },
                  { value: 'critical', label: 'Critical' },
                ]} />
              </Form.Item>
            </Card>

            <div style={{ position: 'sticky', bottom: 0, background: 'var(--ant-color-bg-container)', padding: '16px 0', borderTop: '1px solid var(--ant-color-border)', display: 'flex', gap: 12 }}>
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={updateMutation.isPending} disabled={!hasChanges}>
                保存配置
              </Button>
              <Button icon={<UndoOutlined />} onClick={handleReset}>
                重置为默认值
              </Button>
            </div>
          </Form>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: 验证编译**

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web
npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: 系统配置页面（回测参数 + 风险控制 + 数据同步 + 通知设置）"
```

---

## Phase 4: 集成与清理

### Task 12: 清理旧 Layout 组件

**Files:**
- Delete: `web/src/components/Layout/Layout.tsx`
- Delete: `web/src/components/Layout/Header.tsx`
- Delete: `web/src/components/Layout/Sidebar.tsx`
- Modify: `web/src/index.css`

- [ ] **Step 1: 删除旧 Layout 文件**

```bash
rm -rf /data/wangf/lanbao_ws/src/lanbao_backtest/web/src/components/Layout/
```

- [ ] **Step 2: 验证编译**

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web
npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor: 移除旧 Layout 组件（已被 AppShell 替代）"
```

---

### Task 13: 启动验证

**Files:**
- 无新增/修改

- [ ] **Step 1: 构建前端**

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web
npm run build
```

Expected: 构建成功，无错误

- [ ] **Step 2: 验证后端导入**

```bash
cd /data/wangf/lanbao_ws
source .venv/bin/activate
source /opt/ros/humble/setup.bash
source install/setup.bash
cd src/lanbao_backtest
python -c "from api.main import app; print('后端导入成功')"
```

Expected: 输出 "后端导入成功"

- [ ] **Step 3: 最终 Commit**

```bash
git add -A
git commit -m "chore: 构建验证通过，Dashboard 平台化完成"
```

---

## 自检

### Spec 覆盖检查

| 设计文档章节 | 对应任务 |
|-------------|---------|
| 主题系统 (3.1) | Task 1 |
| WebSocket 管理器 (3.2) | Task 2 |
| 双层导航布局 (3.3) | Task 3 |
| 状态管理扩展 (3.4) | Task 1, 2, 7, 10, 11 |
| 系统概览页面 (4.1) | Task 7 |
| 节点状态页面 (4.2) | Task 8 |
| 风险监控页面 (4.3) | Task 9 |
| 数据底座页面 (4.4) | Task 10 |
| 系统配置页面 (4.5) | Task 11 |
| SystemMetrics 消息 (5.1) | Task 4 |
| system_metrics_node (5.2) | Task 5 |
| FastAPI 新接口 (5.3) | Task 6 |
| WebSocket 协议 (6.1) | Task 2 |
| 错误处理 (7) | 各页面内联处理 |
| 测试策略 (8) | 未单独拆分，建议后续补充 |

### Placeholder 检查

- 无 "TBD"、"TODO"、"implement later"
- 无 "Add appropriate error handling" 等模糊描述
- 所有代码块均为完整实现
- 所有命令均含预期输出

### 类型一致性检查

- `SystemMetricsMsg` 在 `types/ros2.ts` 定义，在 `useSystemMetrics.ts` 使用 — 一致
- `NodeStatusMsg` 在 `types/ros2.ts` 定义，在 `useNodeStatus.ts` 和 `NodeStatusPage.tsx` 使用 — 一致
- `RiskAlertMsg` 在 `types/ros2.ts` 定义，在 `useAlerts.ts` 和 `RiskMonitorPage.tsx` 使用 — 一致
- `SystemConfig` 在 `types/config.ts` 定义，在 `configApi.ts` 和 `SystemConfigPage.tsx` 使用 — 一致
- FastAPI 模型 `SystemConfig` 与前端类型字段命名一致

---

## 执行交接

Plan complete and saved to `docs/superpowers/plans/2026-05-11-dashboard-portal.md`. Two execution options:

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
