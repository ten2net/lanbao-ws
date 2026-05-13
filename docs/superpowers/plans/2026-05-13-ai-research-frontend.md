# 揽宝智能投研模块（前端 Portal）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 React + Vite + Ant Design Portal 中集成智能投研功能页面

**Architecture:** 新增「智能投研」导航分组，含市场日报、个股研究、报告历史三个页面，通过 TanStack Query 调用后端 API

**Tech Stack:** React 18, TypeScript, Vite, Ant Design 5, TanStack Query, Axios

---

## 文件结构映射

```
src/lanbao_backtest/web/src/
  api/research.ts                    # 新增：投研 API 调用
  hooks/useResearch.ts               # 新增：投研数据 hooks
  components/AIResearch/
    ResearchProgress.tsx             # 新增：分析进度展示
    StockAnalysisCard.tsx            # 新增：个股分析卡片
    ReportViewer.tsx                 # 新增：报告查看器
  pages/
    AIResearchDailyPage.tsx          # 新增：市场日报页面
    AIResearchStockPage.tsx          # 新增：个股研究页面
    AIResearchHistoryPage.tsx        # 新增：报告历史页面
  App.tsx                            # 修改：添加路由
  components/AppShell/SideNav.tsx    # 修改：添加导航
```

---

## Task 1: API 层 — research.ts

**Files:**
- Create: `src/lanbao_backtest/web/src/api/research.ts`

- [ ] **Step 1: 创建 research.ts**

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/web/src/api/research.ts
git commit -m "feat: add research API client for frontend"
```

---

## Task 2: Hooks — useResearch.ts

**Files:**
- Create: `src/lanbao_backtest/web/src/hooks/useResearch.ts`

- [ ] **Step 1: 创建 useResearch.ts**

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { researchApi } from '../api/research';

export const useTriggerMarketDaily = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: researchApi.triggerMarketDaily,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['research-reports'] });
    },
  });
};

export const useTriggerStockResearch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: researchApi.triggerStockResearch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['research-reports'] });
    },
  });
};

export const useResearchStatus = (reportId: string | null) => {
  return useQuery({
    queryKey: ['research-status', reportId],
    queryFn: () => researchApi.getStatus(reportId!),
    enabled: !!reportId,
    refetchInterval: (data) =>
      data?.status === 'running' ? 3000 : false,
  });
};

export const useResearchReport = (reportId: string | null) => {
  return useQuery({
    queryKey: ['research-report', reportId],
    queryFn: () => researchApi.getReport(reportId!),
    enabled: !!reportId,
  });
};

export const useResearchReports = (params?: { report_type?: string; limit?: number; offset?: number }) => {
  return useQuery({
    queryKey: ['research-reports', params],
    queryFn: () => researchApi.listReports(params),
  });
};
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/web/src/hooks/useResearch.ts
git commit -m "feat: add useResearch hooks with TanStack Query"
```

---

## Task 3: 组件 — ResearchProgress.tsx

**Files:**
- Create: `src/lanbao_backtest/web/src/components/AIResearch/ResearchProgress.tsx`

- [ ] **Step 1: 创建组件目录和文件**

```typescript
import React from 'react';
import { Card, Progress, Steps, Tag } from 'antd';
import { CheckCircleOutlined, LoadingOutlined, ClockCircleOutlined } from '@ant-design/icons';

interface ResearchProgressProps {
  status: string;
  progress: number;
  message: string;
  currentAgent?: string;
}

const agentSteps = [
  { title: '宏观分析', key: 'macro_analyst' },
  { title: '基本面分析', key: 'fundamental_analyst' },
  { title: '技术面分析', key: 'technical_analyst' },
  { title: '情绪新闻', key: 'sentiment_news_analyst' },
  { title: '投资总监', key: 'portfolio_director' },
];

export const ResearchProgress: React.FC<ResearchProgressProps> = ({
  status,
  progress,
  message,
  currentAgent,
}) => {
  const isRunning = status === 'running';
  const isCompleted = status === 'completed';

  const getCurrentStep = () => {
    if (!currentAgent) return -1;
    return agentSteps.findIndex(s => s.key === currentAgent);
  };

  return (
    <Card title="分析进度" bordered={false}>
      <Progress
        percent={Math.round(progress * 100)}
        status={isCompleted ? 'success' : isRunning ? 'active' : 'normal'}
      />
      <div style={{ marginTop: 16 }}>
        <Tag icon={isRunning ? <LoadingOutlined /> : isCompleted ? <CheckCircleOutlined /> : <ClockCircleOutlined />}>
          {message}
        </Tag>
      </div>
      <Steps
        direction="vertical"
        size="small"
        current={getCurrentStep()}
        items={agentSteps.map(step => ({
          title: step.title,
          icon: getCurrentStep() > agentSteps.indexOf(step) ? <CheckCircleOutlined /> : undefined,
        }))}
        style={{ marginTop: 24 }}
      />
    </Card>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/web/src/components/AIResearch/ResearchProgress.tsx
git commit -m "feat: add ResearchProgress component"
```

---

## Task 4: 组件 — StockAnalysisCard.tsx

**Files:**
- Create: `src/lanbao_backtest/web/src/components/AIResearch/StockAnalysisCard.tsx`

- [ ] **Step 1: 创建组件**

```typescript
import React from 'react';
import { Card, Tag, Row, Col, Statistic, List, Typography } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';

interface StockAnalysisCardProps {
  symbol: string;
  name?: string;
  synthesis?: {
    verdict: string;
    score: number;
    bull_case: string[];
    bear_case: string[];
    position_suggestion: string;
    risk_notes: string[];
  };
}

const verdictColors: Record<string, string> = {
  STRONG_BUY: 'green',
  BUY: 'cyan',
  HOLD: 'blue',
  SELL: 'orange',
  STRONG_SELL: 'red',
};

const verdictLabels: Record<string, string> = {
  STRONG_BUY: '强力买入',
  BUY: '买入',
  HOLD: '持有',
  SELL: '卖出',
  STRONG_SELL: '强力卖出',
};

export const StockAnalysisCard: React.FC<StockAnalysisCardProps> = ({
  symbol,
  name,
  synthesis,
}) => {
  if (!synthesis) {
    return (
      <Card title={`${symbol} ${name || ''}`} size="small">
        <Typography.Text type="secondary">分析数据不可用</Typography.Text>
      </Card>
    );
  }

  return (
    <Card
      title={
        <span>
          {symbol} {name}
          <Tag color={verdictColors[synthesis.verdict]} style={{ marginLeft: 8 }}>
            {verdictLabels[synthesis.verdict] || synthesis.verdict}
          </Tag>
        </span>
      }
      size="small"
    >
      <Row gutter={16}>
        <Col span={8}>
          <Statistic
            title="综合得分"
            value={synthesis.score}
            suffix="/100"
            valueStyle={{ color: synthesis.score >= 70 ? '#3f8600' : synthesis.score >= 50 ? '#1890ff' : '#cf1322' }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="仓位建议"
            value={synthesis.position_suggestion}
          />
        </Col>
        <Col span={8}>
          <div>
            <Typography.Text type="secondary">风险:</Typography.Text>
            <div>
              {synthesis.risk_notes.map((note, i) => (
                <Tag key={i} color="warning" style={{ marginTop: 4 }}>{note}</Tag>
              ))}
            </div>
          </div>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Typography.Title level={5}><ArrowUpOutlined style={{ color: 'green' }} /> 看多理由</Typography.Title>
          <List
            size="small"
            dataSource={synthesis.bull_case}
            renderItem={(item) => <List.Item>{item}</List.Item>}
          />
        </Col>
        <Col span={12}>
          <Typography.Title level={5}><ArrowDownOutlined style={{ color: 'red' }} /> 看空理由</Typography.Title>
          <List
            size="small"
            dataSource={synthesis.bear_case}
            renderItem={(item) => <List.Item>{item}</List.Item>}
          />
        </Col>
      </Row>
    </Card>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/web/src/components/AIResearch/StockAnalysisCard.tsx
git commit -m "feat: add StockAnalysisCard component"
```

---

## Task 5: 页面 — AIResearchDailyPage.tsx

**Files:**
- Create: `src/lanbao_backtest/web/src/pages/AIResearchDailyPage.tsx`

- [ ] **Step 1: 创建页面**

```typescript
import React, { useState } from 'react';
import { Card, Button, Table, Tag, Typography, message, Space, Descriptions } from 'antd';
import { FileTextOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useResearchReports, useTriggerMarketDaily } from '../hooks/useResearch';

const { Title, Text } = Typography;

const verdictColors: Record<string, string> = {
  STRONG_BUY: 'green', BUY: 'cyan', HOLD: 'blue', SELL: 'orange', STRONG_SELL: 'red',
};

export const AIResearchDailyPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: reportsData, isLoading } = useResearchReports({ limit: 50 });
  const triggerDaily = useTriggerMarketDaily();
  const [generating, setGenerating] = useState(false);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const result = await triggerDaily.mutateAsync();
      message.success(`已开始生成日报: ${result.report_id}`);
      // 跳转到个股研究页面查看进度
      navigate(`/ai-research/stock?reportId=${result.report_id}`);
    } catch (e) {
      message.error('生成日报失败');
    } finally {
      setGenerating(false);
    }
  };

  const columns = [
    {
      title: '日期',
      dataIndex: 'created_at',
      key: 'date',
    },
    {
      title: '报告ID',
      dataIndex: 'report_id',
      key: 'report_id',
      render: (id: string) => (
        <Button type="link" onClick={() => navigate(`/ai-research/history?reportId=${id}`)}>
          {id}
        </Button>
      ),
    },
    {
      title: '综合评级',
      key: 'verdict',
      render: (_: any, record: any) => {
        // 需要从报告详情获取评级，简化显示
        return <Tag>查看详情</Tag>;
      },
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Space style={{ justifyContent: 'space-between', width: '100%' }}>
            <Title level={4} style={{ margin: 0 }}><FileTextOutlined /> 市场日报</Title>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              loading={generating}
              onClick={handleGenerate}
            >
              生成今日报告
            </Button>
          </Space>
        </Card>

        <Card title="历史日报" loading={isLoading}>
          <Table
            dataSource={reportsData?.reports || []}
            columns={columns}
            rowKey="report_id"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      </Space>
    </div>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/web/src/pages/AIResearchDailyPage.tsx
git commit -m "feat: add AIResearchDailyPage"
```

---

## Task 6: 页面 — AIResearchStockPage.tsx

**Files:**
- Create: `src/lanbao_backtest/web/src/pages/AIResearchStockPage.tsx`

- [ ] **Step 1: 创建页面**

```typescript
import React, { useState, useEffect } from 'react';
import { Card, Input, Button, message, Space, Typography } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import { useTriggerStockResearch, useResearchStatus, useResearchReport } from '../hooks/useResearch';
import { ResearchProgress } from '../components/AIResearch/ResearchProgress';
import { StockAnalysisCard } from '../components/AIResearch/StockAnalysisCard';

const { Title } = Typography;

export const AIResearchStockPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [symbol, setSymbol] = useState('');
  const [activeReportId, setActiveReportId] = useState<string | null>(searchParams.get('reportId'));

  const triggerStock = useTriggerStockResearch();
  const { data: statusData } = useResearchStatus(activeReportId);
  const { data: reportData } = useResearchReport(
    statusData?.status === 'completed' ? activeReportId : null
  );

  useEffect(() => {
    const reportId = searchParams.get('reportId');
    if (reportId) {
      setActiveReportId(reportId);
    }
  }, [searchParams]);

  const handleAnalyze = async () => {
    if (!symbol.trim()) {
      message.warning('请输入股票代码');
      return;
    }
    try {
      const result = await triggerStock.mutateAsync(symbol.trim());
      setActiveReportId(result.report_id);
      setSearchParams({ reportId: result.report_id });
      message.success(`已开始分析: ${symbol}`);
    } catch (e) {
      message.error('分析失败');
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Title level={4}>个股智能研究</Title>
          <Space.Compact style={{ width: '100%', maxWidth: 500 }}>
            <Input
              placeholder="请输入股票代码 (如: 600519)"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              onPressEnter={handleAnalyze}
              prefix={<SearchOutlined />}
            />
            <Button type="primary" onClick={handleAnalyze} loading={triggerStock.isPending}>
              开始分析
            </Button>
          </Space.Compact>
        </Card>

        {activeReportId && statusData && (
          <ResearchProgress
            status={statusData.status}
            progress={statusData.progress}
            message={statusData.message}
            currentAgent={statusData.current_agent}
          />
        )}

        {reportData && (
          <Card title="分析报告">
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div>
                <Title level={5}>市场综述</Title>
                <p>综合评级: <strong>{reportData.summary.overall_verdict}</strong></p>
                <p>置信度: {(reportData.summary.confidence * 100).toFixed(0)}%</p>
              </div>

              {reportData.stock_analyses?.map((stock) => (
                <StockAnalysisCard
                  key={stock.symbol}
                  symbol={stock.symbol}
                  name={stock.name}
                  synthesis={stock.synthesis}
                />
              ))}
            </Space>
          </Card>
        )}
      </Space>
    </div>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/web/src/pages/AIResearchStockPage.tsx
git commit -m "feat: add AIResearchStockPage with progress and analysis"
```

---

## Task 7: 页面 — AIResearchHistoryPage.tsx

**Files:**
- Create: `src/lanbao_backtest/web/src/pages/AIResearchHistoryPage.tsx`

- [ ] **Step 1: 创建页面**

```typescript
import React, { useState } from 'react';
import { Card, Table, Button, Tag, Space, Typography, DatePicker } from 'antd';
import { HistoryOutlined, EyeOutlined, DownloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useResearchReports } from '../hooks/useResearch';

const { Title } = Typography;

export const AIResearchHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const { data, isLoading } = useResearchReports({ limit: pageSize, offset: (page - 1) * pageSize });

  const columns = [
    { title: '报告ID', dataIndex: 'report_id', key: 'report_id' },
    { title: '生成日期', dataIndex: 'created_at', key: 'created_at' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/ai-research/stock?reportId=${record.report_id}`)}
          >
            查看
          </Button>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => window.open(`/reports/${record.created_at}/${record.report_id}.md`, '_blank')}
          >
            下载
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Title level={4}><HistoryOutlined /> 报告历史</Title>
        <Table
          dataSource={data?.reports || []}
          columns={columns}
          rowKey="report_id"
          loading={isLoading}
          pagination={{
            current: page,
            pageSize,
            total: data?.total || 0,
            onChange: setPage,
          }}
        />
      </Card>
    </div>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add src/lanbao_backtest/web/src/pages/AIResearchHistoryPage.tsx
git commit -m "feat: add AIResearchHistoryPage"
```

---

## Task 8: 注册路由和导航

**Files:**
- Modify: `src/lanbao_backtest/web/src/App.tsx`
- Modify: `src/lanbao_backtest/web/src/components/AppShell/SideNav.tsx`

- [ ] **Step 1: 修改 App.tsx**

Read existing App.tsx, then add imports:
```typescript
import { AIResearchDailyPage } from './pages/AIResearchDailyPage';
import { AIResearchStockPage } from './pages/AIResearchStockPage';
import { AIResearchHistoryPage } from './pages/AIResearchHistoryPage';
```

Add routes inside the AppShell Route:
```typescript
<Route path="/ai-research/daily" element={<AIResearchDailyPage />} />
<Route path="/ai-research/stock" element={<AIResearchStockPage />} />
<Route path="/ai-research/history" element={<AIResearchHistoryPage />} />
```

- [ ] **Step 2: 修改 SideNav.tsx**

Read existing SideNav.tsx, then add a new module group:

```typescript
ai_research: [
  { key: '/ai-research/daily', label: '市场日报', icon: <FileTextOutlined /> },
  { key: '/ai-research/stock', label: '个股研究', icon: <SearchOutlined /> },
  { key: '/ai-research/history', label: '报告历史', icon: <HistoryOutlined /> },
],
```

Add imports for FileTextOutlined, SearchOutlined, HistoryOutlined.

- [ ] **Step 3: Commit**

```bash
git add src/lanbao_backtest/web/src/App.tsx src/lanbao_backtest/web/src/components/AppShell/SideNav.tsx
git commit -m "feat: register AI research routes and navigation"
```

---

## Task 9: 构建验证

- [ ] **Step 1: 构建前端**

```bash
cd /data/wangf/lanbao_ws/src/lanbao_backtest/web
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 2: Commit**

```bash
git commit -m "chore: verify frontend build" --allow-empty
```
