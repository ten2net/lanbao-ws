import { useState, useMemo, useCallback } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Statistic,
  Row,
  Col,
  Progress,
  Drawer,
  message,
} from 'antd';
import { EyeOutlined, SyncOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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

// Static columns (no component state dependency)
const staticTableColumns = [
  {
    title: '表名',
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: '记录数',
    dataIndex: 'record_count',
    key: 'record_count',
    render: (v: number) => formatNumber(v),
  },
  {
    title: '数据起始日期',
    dataIndex: 'date_start',
    key: 'date_start',
    render: (v?: string) => v || '-',
  },
  {
    title: '数据结束日期',
    dataIndex: 'date_end',
    key: 'date_end',
    render: (v?: string) => v || '-',
  },
  {
    title: '更新时间',
    dataIndex: 'last_updated',
    key: 'last_updated',
    render: (v?: string) => v || '-',
  },
  {
    title: '质量评分',
    dataIndex: 'quality_score',
    key: 'quality_score',
    render: (v: number) => (
      <Tag color={qualityColor(v)}>{v}</Tag>
    ),
  },
];

const syncColumns = [
  {
    title: '数据源',
    dataIndex: 'source',
    key: 'source',
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    render: (v: string) => {
      const color = v === 'completed' ? 'green' : v === 'running' ? 'blue' : v === 'failed' ? 'red' : 'default';
      return <Tag color={color}>{v}</Tag>;
    },
  },
  {
    title: '进度',
    dataIndex: 'progress',
    key: 'progress',
    render: (v: number) => <Progress percent={v} size="small" />,
  },
  {
    title: '成功数',
    dataIndex: 'success_count',
    key: 'success_count',
  },
  {
    title: '失败数',
    dataIndex: 'failed_count',
    key: 'failed_count',
  },
  {
    title: '耗时(秒)',
    dataIndex: 'duration_seconds',
    key: 'duration_seconds',
    render: (v: number | null) => (v !== null ? `${v}s` : '-'),
  },
];

const qualityColumns = [
  {
    title: '表名',
    dataIndex: 'table',
    key: 'table',
  },
  {
    title: '缺失率',
    dataIndex: 'missing_rate',
    key: 'missing_rate',
    render: (v: number) => `${(v * 100).toFixed(2)}%`,
  },
  {
    title: '覆盖评分',
    dataIndex: 'coverage_score',
    key: 'coverage_score',
  },
  {
    title: '综合评分',
    dataIndex: 'overall_score',
    key: 'overall_score',
    render: (v: number) => (
      <Tag color={qualityColor(v)}>{v}</Tag>
    ),
  },
];

export function DataCenterPage() {
  const [previewTable, setPreviewTable] = useState<string | null>(null);
  const qc = useQueryClient();

  const { data: summary } = useQuery({
    queryKey: ['data', 'summary'],
    queryFn: dataApi.summary,
  });

  const { data: tables } = useQuery({
    queryKey: ['data', 'tables'],
    queryFn: dataApi.tables,
  });

  const { data: syncTasks } = useQuery({
    queryKey: ['data', 'sync'],
    queryFn: dataApi.syncStatus,
  });

  const { data: quality } = useQuery({
    queryKey: ['data', 'quality'],
    queryFn: () => dataApi.quality(),
  });

  const triggerSyncMutation = useMutation({
    mutationFn: dataApi.triggerSync,
    onSuccess: () => {
      message.success('同步任务已触发');
      qc.invalidateQueries({ queryKey: ['data', 'sync'] });
      qc.invalidateQueries({ queryKey: ['data', 'summary'] });
    },
    onError: (err: Error) => {
      message.error(`同步失败: ${err.message}`);
    },
  });

  const handlePreview = useCallback((name: string) => {
    setPreviewTable(name);
  }, []);

  const tableColumns = useMemo(() => [
    ...staticTableColumns,
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: DataTableInfo) => (
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handlePreview(record.name)}
        >
          预览
        </Button>
      ),
    },
  ], [handlePreview]);

  const tableData = useMemo(() => tables || [], [tables]);
  const syncData = useMemo(() => syncTasks || [], [syncTasks]);
  const qualityData = useMemo(() => quality || [], [quality]);

  return (
    <div style={{ padding: 24 }}>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={12} md={6}>
          <Card>
            <Statistic title="总股票数" value={summary?.total_symbols ?? 0} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic
              title="日线数据条数"
              value={formatNumber(summary?.total_daily_records ?? 0)}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic
              title="最后同步时间"
              value={summary?.last_sync_time ?? '-'}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic
              title="数据覆盖天数"
              value={summary?.coverage_days ?? 0}
            />
          </Card>
        </Col>
      </Row>

      {/* 数据表列表 */}
      <Card style={{ marginTop: 16 }} title="数据表">
        <Table
          dataSource={tableData}
          columns={tableColumns}
          rowKey="name"
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 底部两栏 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card
            title="同步状态"
            extra={
              <Button
                type="primary"
                icon={<SyncOutlined />}
                loading={triggerSyncMutation.isPending}
                onClick={() => triggerSyncMutation.mutate(undefined)}
              >
                手动同步
              </Button>
            }
          >
            <Table
              dataSource={syncData}
              columns={syncColumns}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 5 }}
            />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="数据质量">
            <Table
              dataSource={qualityData}
              columns={qualityColumns}
              rowKey="table"
              size="small"
              pagination={{ pageSize: 5 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 预览 Drawer */}
      <Drawer
        title={`预览: ${previewTable}`}
        width={600}
        open={!!previewTable}
        onClose={() => setPreviewTable(null)}
      >
        {previewTable && (
          <div>
            <p>表名: {previewTable}</p>
            <p>显示前 100 行数据预览...</p>
          </div>
        )}
      </Drawer>
    </div>
  );
}
