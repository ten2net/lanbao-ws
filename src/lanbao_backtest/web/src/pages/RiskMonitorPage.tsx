import { useState, useMemo } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Statistic,
  Row,
  Col,
  notification,
} from 'antd';
import { CheckOutlined, EyeInvisibleOutlined } from '@ant-design/icons';
import { useAlerts } from '../hooks/useAlerts';
import { useMonitorStore } from '../stores/monitorStore';
import { MetricChart } from '../components/Monitor/MetricChart';
import { AlertBadge } from '../components/Monitor/AlertBadge';
import type { RiskAlertMsg } from '../types/ros2';

type LevelFilter = 'ALL' | RiskAlertMsg['level'];

const FILTER_OPTIONS: { key: LevelFilter; label: string }[] = [
  { key: 'ALL', label: '全部' },
  { key: 'CRITICAL', label: '严重' },
  { key: 'HIGH', label: '高' },
  { key: 'MEDIUM', label: '中' },
  { key: 'LOW', label: '低' },
];

const TYPE_LABEL: Record<RiskAlertMsg['alert_type'], string> = {
  POSITION: '仓位',
  DRAWDOWN: '回撤',
  VOLATILITY: '波动率',
  SYSTEM: '系统',
};

function formatTime(sec: number): string {
  return new Date(sec * 1000).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function RiskMonitorPage() {
  useAlerts();

  const alerts = useMonitorStore((state) => state.alerts);
  const [levelFilter, setLevelFilter] = useState<LevelFilter>('ALL');
  const [acknowledgedIds, setAcknowledgedIds] = useState<Set<string>>(new Set());

  const todayAlerts = useMemo(() => {
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    return alerts.filter((a) => a.timestamp * 1000 >= startOfDay);
  }, [alerts]);

  const stats = useMemo(() => {
    const total = todayAlerts.length;
    const critical = todayAlerts.filter((a) => a.level === 'CRITICAL').length;
    const warning = todayAlerts.filter((a) => a.level === 'HIGH' || a.level === 'MEDIUM').length;
    const acknowledged = todayAlerts.filter((a) => acknowledgedIds.has(a.alert_id)).length;
    return { total, critical, warning, acknowledged };
  }, [todayAlerts, acknowledgedIds]);

  const trendData = useMemo(
    () =>
      Array.from({ length: 24 }, (_, i) => ({
        time: `${i}:00`,
        value: Math.floor(Math.random() * 5),
      })),
    [],
  );

  const filteredAlerts = useMemo(() => {
    if (levelFilter === 'ALL') return alerts;
    return alerts.filter((a) => a.level === levelFilter);
  }, [alerts, levelFilter]);

  const handleAcknowledge = (alert: RiskAlertMsg) => {
    setAcknowledgedIds((prev) => new Set(prev).add(alert.alert_id));
    notification.success({
      message: '告警已确认',
      description: alert.message,
      duration: 3,
    });
  };

  const handleIgnore = (_alert: RiskAlertMsg) => {
    // 占位：无实际操作
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp: number) => formatTime(timestamp),
      width: 100,
    },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      render: (level: string) => <AlertBadge level={level} />,
      width: 80,
    },
    {
      title: '类型',
      dataIndex: 'alert_type',
      key: 'alert_type',
      render: (type: RiskAlertMsg['alert_type']) => (
        <Tag>{TYPE_LABEL[type] || type}</Tag>
      ),
      width: 80,
    },
    {
      title: '描述',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: '当前值 / 阈值',
      key: 'value_threshold',
      render: (_: unknown, record: RiskAlertMsg) => (
        <span>
          {record.current_value.toFixed(2)} / {record.threshold.toFixed(2)}
        </span>
      ),
      width: 140,
    },
    {
      title: '关联策略',
      dataIndex: 'affected_strategies',
      key: 'affected_strategies',
      render: (strategies: string[]) => (
        <span style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {strategies.map((s) => (
            <Tag key={s}>
              {s}
            </Tag>
          ))}
        </span>
      ),
      width: 160,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: RiskAlertMsg) => (
        <span style={{ display: 'flex', gap: 8 }}>
          <Button
            size="small"
            icon={<CheckOutlined />}
            onClick={() => handleAcknowledge(record)}
            disabled={acknowledgedIds.has(record.alert_id)}
          >
            确认
          </Button>
          <Button
            size="small"
            icon={<EyeInvisibleOutlined />}
            onClick={() => handleIgnore(record)}
          >
            忽略
          </Button>
        </span>
      ),
      width: 160,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* 统计栏 */}
      <Row gutter={[16, 16]}>
        <Col xs={12} md={6}>
          <Card>
            <Statistic title="今日告警总数" value={stats.total} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic title="严重告警数" value={stats.critical} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic title="警告告警数" value={stats.warning} valueStyle={{ color: '#faad14' }} />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic title="已处理数" value={stats.acknowledged} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
      </Row>

      {/* 告警趋势图 */}
      <Card style={{ marginTop: 16 }}>
        <MetricChart data={trendData} title="24小时告警趋势" color="#ff4d4f" />
      </Card>

      {/* 告警表格 */}
      <Card style={{ marginTop: 16 }}>
        <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {FILTER_OPTIONS.map((opt) => {
            const count =
              opt.key === 'ALL'
                ? alerts.length
                : alerts.filter((a) => a.level === opt.key).length;
            const active = levelFilter === opt.key;
            return (
              <Tag
                key={opt.key}
                color={active ? 'blue' : undefined}
                style={{ cursor: 'pointer' }}
                onClick={() => setLevelFilter(opt.key)}
              >
                {opt.label} ({count})
              </Tag>
            );
          })}
        </div>

        <Table
          dataSource={filteredAlerts}
          columns={columns}
          rowKey="alert_id"
          size="small"
          pagination={{ pageSize: 20 }}
          scroll={{ x: 'max-content' }}
        />
      </Card>
    </div>
  );
}
