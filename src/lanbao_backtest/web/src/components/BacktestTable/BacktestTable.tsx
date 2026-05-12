import { Table, Tag, Space, Button, Popconfirm, Pagination, Select, Input, Tooltip } from 'antd';
import { DeleteOutlined, EyeOutlined, BarChartOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useBacktestList, useDeleteBacktest } from '../../hooks/useBacktests';
import { useBacktestStore } from '../../stores/backtestStore';
import type { BacktestListItem } from '../../types/backtest';

const { Option } = Select;

const statusColors: Record<string, string> = {
  completed: 'success',
  running: 'processing',
  failed: 'error',
  pending: 'default',
};

const statusLabels: Record<string, string> = {
  completed: '已完成',
  running: '运行中',
  failed: '失败',
  pending: '待处理',
};

function formatPct(val: number | null) {
  if (val == null) return '-';
  const fixed = val.toFixed(2);
  return `${fixed}%`;
}

function formatColor(val: number | null) {
  if (val == null) return '';
  return val >= 0 ? 'rgb(207, 48, 74)' : 'rgb(34, 139, 34)';
}

export function BacktestTable() {
  const navigate = useNavigate();
  const { filters, page, limit, setPage, setFilters } = useBacktestStore();
  const { data, isLoading } = useBacktestList();
  const deleteMutation = useDeleteBacktest();

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const columns = [
    {
      title: '策略',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
      render: (_: string, record: BacktestListItem) => (
        <span>{record.strategy_name || record.strategy_id}</span>
      ),
    },
    {
      title: '标的',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: '日期范围',
      key: 'dateRange',
      render: (_: any, record: BacktestListItem) => (
        <span>{record.start_date} ~ {record.end_date}</span>
      ),
    },
    {
      title: '总收益',
      dataIndex: 'total_return',
      key: 'total_return',
      render: (val: number | null) => (
        <span style={{ color: formatColor(val), fontWeight: 600 }}>{formatPct(val)}</span>
      ),
    },
    {
      title: '年化收益',
      dataIndex: 'annual_return',
      key: 'annual_return',
      render: (val: number | null) => (
        <span style={{ color: formatColor(val) }}>{formatPct(val)}</span>
      ),
    },
    {
      title: '夏普比率',
      dataIndex: 'sharpe_ratio',
      key: 'sharpe_ratio',
      render: (val: number | null) => (
        <span style={{ fontWeight: 600 }}>{val != null ? val.toFixed(2) : '-'}</span>
      ),
    },
    {
      title: '最大回撤',
      dataIndex: 'max_drawdown',
      key: 'max_drawdown',
      render: (val: number | null) => (
        <span style={{ color: 'rgb(34, 139, 34)' }}>{formatPct(val)}</span>
      ),
    },
    {
      title: '胜率',
      dataIndex: 'win_rate',
      key: 'win_rate',
      render: (val: number | null) => (
        <span>{val != null ? `${val.toFixed(1)}%` : '-'}</span>
      ),
    },
    {
      title: '交易次数',
      dataIndex: 'trade_count',
      key: 'trade_count',
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <Space size={4}>
          {tags.map((tag) => (
            <Tag key={tag} color="blue" style={{ fontSize: 12 }}>{tag}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColors[status] || 'default'}>{statusLabels[status] || status}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: BacktestListItem) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              icon={<EyeOutlined />}
              size="small"
              onClick={() => navigate(`/backtest/${record.backtest_id}`)}
            />
          </Tooltip>
          <Tooltip title="参数分析">
            <Button
              icon={<BarChartOutlined />}
              size="small"
              onClick={() => navigate(`/param-analysis?backtestId=${record.backtest_id}`)}
            />
          </Tooltip>
          <Popconfirm
            title="确认删除"
            description="删除后无法恢复，确认删除该回测？"
            onConfirm={() => deleteMutation.mutate(record.backtest_id)}
            okText="删除"
            cancelText="取消"
          >
            <Button icon={<DeleteOutlined />} size="small" danger loading={deleteMutation.isPending} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="筛选策略"
          allowClear
          style={{ width: 160 }}
          value={filters.strategy}
          onChange={(v) => setFilters({ strategy: v })}
        >
          <Option value="ma_cross">双均线交叉</Option>
          <Option value="rsi">RSI策略</Option>
          <Option value="macd">MACD策略</Option>
        </Select>
        <Input.Search
          placeholder="股票代码"
          allowClear
          style={{ width: 160 }}
          value={filters.symbol}
          onSearch={(v) => setFilters({ symbol: v || undefined })}
          onChange={(e) => {
            if (!e.target.value) setFilters({ symbol: undefined });
          }}
        />
        <Button onClick={() => setFilters({ strategy: undefined, symbol: undefined, tags: [] })}>
          重置筛选
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={items}
        rowKey="backtest_id"
        loading={isLoading}
        pagination={false}
        size="small"
        scroll={{ x: 1200 }}
      />

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
        <Pagination
          current={page}
          pageSize={limit}
          total={total}
          showSizeChanger={false}
          onChange={(p) => setPage(p)}
          showTotal={(t) => `共 ${t} 条`}
        />
      </div>
    </div>
  );
}
