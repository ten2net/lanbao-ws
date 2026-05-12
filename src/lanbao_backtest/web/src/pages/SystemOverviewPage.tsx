import { useMemo } from 'react';
import { Row, Col, Card, List, Tag, Badge } from 'antd';
import { useMonitorStore } from '../stores/monitorStore';
import { useSystemMetrics } from '../hooks/useSystemMetrics';
import { useNodeStatus } from '../hooks/useNodeStatus';
import { useAlerts } from '../hooks/useAlerts';
import { KPIGrid } from '../components/Monitor/KPIGrid';
import { MetricChart } from '../components/Monitor/MetricChart';
import { StatusPieChart } from '../components/Monitor/StatusPieChart';
import type { NodeStatusMsg, SystemAlertMsg } from '../types/ros2';

function formatTime(sec: number): string {
  return new Date(sec * 1000).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function getAlertColor(type: SystemAlertMsg['alert_type']): string {
  switch (type) {
    case 'CRITICAL':
      return 'red';
    case 'ERROR':
      return 'orange';
    case 'WARNING':
      return 'gold';
    case 'INFO':
    default:
      return 'blue';
  }
}

export function SystemOverviewPage() {
  useSystemMetrics();
  useNodeStatus();
  useAlerts();

  const nodes = useMonitorStore((state) => state.nodes);
  const alerts = useMonitorStore((state) => state.alerts);
  const metricsHistory = useMonitorStore((state) => state.metricsHistory);

  const onlineNodes = useMemo(
    () => nodes.filter((n) => n.status === 'RUNNING').length,
    [nodes],
  );

  const todayAlertCount = useMemo(() => {
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    return alerts.filter((a) => a.timestamp * 1000 >= startOfDay).length;
  }, [alerts]);

  const latestCpu = useMemo(() => {
    const last = metricsHistory[metricsHistory.length - 1];
    return last ? last.cpu_percent : 0;
  }, [metricsHistory]);

  const latestMemory = useMemo(() => {
    const last = metricsHistory[metricsHistory.length - 1];
    return last ? last.memory_percent : 0;
  }, [metricsHistory]);

  const cpuData = useMemo(
    () =>
      metricsHistory.map((m) => ({
        time: formatTime(m.timestamp.sec),
        value: Number(m.cpu_percent.toFixed(1)),
      })),
    [metricsHistory],
  );

  const memoryData = useMemo(
    () =>
      metricsHistory.map((m) => ({
        time: formatTime(m.timestamp.sec),
        value: Number(m.memory_percent.toFixed(1)),
      })),
    [metricsHistory],
  );

  const nodeStatusData = useMemo(() => {
    const counts: Record<string, number> = {};
    nodes.forEach((n) => {
      const label = getNodeStatusLabel(n.status);
      counts[label] = (counts[label] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [nodes]);

  const kpiData = [
    { title: '在线节点数', value: onlineNodes },
    { title: '今日告警数', value: todayAlertCount },
    { title: 'CPU 使用率', value: latestCpu, suffix: '%', precision: 1 },
    { title: '内存使用率', value: latestMemory, suffix: '%', precision: 1 },
  ];

  return (
    <div style={{ padding: 24 }}>
      <KPIGrid data={kpiData} />

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card>
            <MetricChart data={cpuData} title="CPU 使用率趋势" color="#1677ff" unit="%" />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <MetricChart data={memoryData} title="内存使用率趋势" color="#52c41a" unit="%" />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <StatusPieChart data={nodeStatusData} title="节点状态分布" />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="最近告警">
            <List
              dataSource={alerts.slice(0, 10)}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={<Badge color={getAlertColor(item.alert_type)} />}
                    title={
                      <span>
                        <Tag color={getAlertColor(item.alert_type)}>{item.alert_type}</Tag>
                        {item.component}
                      </span>
                    }
                    description={
                      <div>
                        <div>{item.message}</div>
                        <div style={{ fontSize: 12, color: '#888' }}>
                          {formatTime(item.timestamp)}
                        </div>
                      </div>
                    }
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

function getNodeStatusLabel(status: NodeStatusMsg['status']): string {
  switch (status) {
    case 'RUNNING':
      return '运行中';
    case 'SYNCING':
      return '同步中';
    case 'ERROR':
      return '错误';
    case 'INITIALIZING':
      return '初始化';
    case 'STOPPED':
      return '已停止';
    default:
      return '未知';
  }
}
