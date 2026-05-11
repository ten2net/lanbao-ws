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
import type { SystemAlertMsg } from '../types/ros2';

type AlertFilter = 'ALL' | SystemAlertMsg['alert_type'];

const FILTER_OPTIONS: { key: AlertFilter; label: string }[] = [
  { key: 'ALL', label: '全部' },
  { key: 'CRITICAL', label: '严重' },
  { key: 'ERROR', label: '错误' },
  { key: 'WARNING', label: '警告' },
  { key: 'INFO', label: '信息' },
];

function formatTime(sec: number): string {
  return new Date(sec * 1000).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function getAlertKey(alert: SystemAlertMsg): string {
  return `${alert.component}-${alert.timestamp}`;
}

export function RiskMonitorPage() {
  useAlerts();

  const alerts = useMonitorStore((state) => state.alerts);
  const [alertFilter, setAlertFilter] = useState<AlertFilter>('ALL');
  const [acknowledgedKeys, setAcknowledgedKeys] = useState<Set<string>>(new Set());

  const todayAlerts = useMemo(() => {
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    return alerts.filter((a) => a.timestamp * 1000 >= startOfDay);
  }, [alerts]);

  const stats = useMemo(() => {
    const total = todayAlerts.length;
    const critical = todayAlerts.filter((a) => a.alert_type === 'CRITICAL').length;
    const warning = todayAlerts.filter((a) => a.alert_type === 'ERROR' || a.alert_type === 'WARNING').length;
    const acknowledged = todayAlerts.filter((a) => acknowledgedKeys.has(getAlertKey(a))).length;
    return { total, critical, warning, acknowledged };
  }, [todayAlerts, acknowledgedKeys]);

  const trendData = useMemo(
    () =>
      Array.from({ length: 24 }, (_, i) => ({
        time: `${i}:00`,
        value: Math.floor(Math.random() * 5),
      })),
    [],
  );

  const filteredAlerts = useMemo(() => {
    if (alertFilter === 'ALL') return alerts;
    return alerts.filter((a) => a.alert_type === alertFilter);
  }, [alerts, alertFilter]);

  const handleAcknowledge = (alert: SystemAlertMsg) => {
    setAcknowledgedKeys((prev) => new Set(prev).add(getAlertKey(alert)));
    notification.success({
      message: '告警已确认',
      description: alert.message,
      duration: 3,
    });
  };

  const handleIgnore = (_alert: SystemAlertMsg) => {
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
      dataIndex: 'alert_type',
      key: 'alert_type',
      render: (type: string) => <AlertBadge level={type} />,
      width: 80,
    },
    {
      title: '组件',
      dataIndex: 'component',
      key: 'component',
      width: 120,
    },
    {
      title: '描述',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: '详情',
      dataIndex: 'details',
      key: 'details',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: SystemAlertMsg) => (
        <span style={{ display: 'flex', gap: 8 }}>
          <Button
            size="small"
            icon={<CheckOutlined />}
            onClick={() => handleAcknowledge(record)}
            disabled={acknowledgedKeys.has(getAlertKey(record))}
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
                : alerts.filter((a) => a.alert_type === opt.key).length;
            const active = alertFilter === opt.key;
            return (
              <Tag
                key={opt.key}
                color={active ? 'blue' : undefined}
                style={{ cursor: 'pointer' }}
                onClick={() => setAlertFilter(opt.key)}
              >
                {opt.label} ({count})
              </Tag>
            );
          })}
        </div>

        <Table
          dataSource={filteredAlerts}
          columns={columns}
          rowKey={(record) => getAlertKey(record)}
          size="small"
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  );
}
