import { useState, useMemo } from 'react';
import {
  Card,
  List,
  Badge,
  Tag,
  Input,
  Row,
  Col,
  Statistic,
  Button,
  Empty,
} from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useNodeStatus } from '../hooks/useNodeStatus';
import { useMonitorStore } from '../stores/monitorStore';
import { MetricChart } from '../components/Monitor/MetricChart';
import type { NodeStatusMsg } from '../types/ros2';

const STATUS_COLOR: Record<NodeStatusMsg['status'], string> = {
  RUNNING: 'green',
  SYNCING: 'cyan',
  INITIALIZING: 'blue',
  ERROR: 'red',
  STOPPED: 'default',
};

const STATUS_LABEL: Record<NodeStatusMsg['status'], string> = {
  RUNNING: '运行中',
  SYNCING: '同步中',
  INITIALIZING: '初始化中',
  ERROR: '错误',
  STOPPED: '已停止',
};

const NODE_NAME_CN: Record<string, string> = {
  market_data_node: '市场数据节点',
  data_sync_node: '数据同步节点',
  backtest_engine_node: '回测引擎节点',
  strategy_manager_node: '策略管理节点',
  risk_control_node: '风险控制节点',
  monitor_node: '监控节点',
  system_metrics_node: '系统指标节点',
};

type StatusFilter = 'ALL' | NodeStatusMsg['status'];

const FILTER_OPTIONS: { key: StatusFilter; label: string }[] = [
  { key: 'ALL', label: '全部' },
  { key: 'RUNNING', label: '运行中' },
  { key: 'SYNCING', label: '同步中' },
  { key: 'INITIALIZING', label: '初始化中' },
  { key: 'ERROR', label: '错误' },
  { key: 'STOPPED', label: '已停止' },
];

function formatTime(sec: number): string {
  return new Date(sec * 1000).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function NodeStatusPage() {
  useNodeStatus();

  const nodes = useMonitorStore((state) => state.nodes);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL');
  const [selectedNodeName, setSelectedNodeName] = useState<string | null>(null);

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    nodes.forEach((n) => {
      counts[n.status] = (counts[n.status] || 0) + 1;
    });
    return counts;
  }, [nodes]);

  const filteredNodes = useMemo(() => {
    let result = nodes;
    if (statusFilter !== 'ALL') {
      result = result.filter((n) => n.status === statusFilter);
    }
    if (searchText.trim()) {
      const lower = searchText.trim().toLowerCase();
      result = result.filter((n) => n.node_name.toLowerCase().includes(lower));
    }
    return result.sort((a, b) => a.node_name.localeCompare(b.node_name));
  }, [nodes, statusFilter, searchText]);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.node_name === selectedNodeName) || null,
    [nodes, selectedNodeName],
  );

  const cpuTrendData = useMemo(() => {
    if (!selectedNode) return [];
    return Array.from({ length: 20 }, (_, i) => ({
      time: `${i}:00`,
      value: Number((selectedNode.cpu_usage + Math.random() * 10 - 5).toFixed(1)),
    }));
  }, [selectedNode]);

  return (
    <div style={{ padding: 24, height: 'calc(100vh - 64px)' }}>
      <Row gutter={[16, 16]} style={{ height: '100%' }}>
        {/* 左侧面板 — 节点列表 */}
        <Col xs={24} md={8} style={{ height: '100%' }}>
          <Card
            title="节点列表"
            style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, overflow: 'auto', padding: '12px' }}
          >
            <Input.Search
              placeholder="搜索节点名称"
              allowClear
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ marginBottom: 12 }}
            />

            <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {FILTER_OPTIONS.map((opt) => {
                const count =
                  opt.key === 'ALL' ? nodes.length : statusCounts[opt.key] || 0;
                const active = statusFilter === opt.key;
                return (
                  <Tag
                    key={opt.key}
                    color={active ? 'blue' : undefined}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setStatusFilter(opt.key)}
                  >
                    {opt.label} ({count})
                  </Tag>
                );
              })}
            </div>

            <List
              dataSource={filteredNodes}
              renderItem={(node) => (
                <List.Item
                  style={{
                    padding: 0,
                    marginBottom: 8,
                    cursor: 'pointer',
                  }}
                  onClick={() => setSelectedNodeName(node.node_name)}
                >
                  <Card
                    size="small"
                    style={{
                      width: '100%',
                      borderColor:
                        selectedNodeName === node.node_name ? '#1677ff' : undefined,
                    }}
                    bodyStyle={{ padding: 12 }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 8,
                      }}
                    >
                      <div>
                        <span style={{ fontWeight: 500 }}>{node.node_name}</span>
                        <span style={{ marginLeft: 8, color: '#888', fontSize: 12 }}>
                          {NODE_NAME_CN[node.node_name] || node.node_type}
                        </span>
                      </div>
                      <Badge
                        status={STATUS_COLOR[node.status] as any}
                        text={STATUS_LABEL[node.status]}
                      />
                    </div>
                    <Row gutter={16}>
                      <Col span={12}>
                        <div style={{ fontSize: 12, color: '#888' }}>
                          CPU: {node.cpu_usage.toFixed(1)}%
                        </div>
                      </Col>
                      <Col span={12}>
                        <div style={{ fontSize: 12, color: '#888' }}>
                          内存: {node.memory_usage.toFixed(1)}%
                        </div>
                      </Col>
                    </Row>
                  </Card>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* 右侧面板 — 节点详情 */}
        <Col xs={24} md={16} style={{ height: '100%' }}>
          {selectedNode ? (
            <Card
              title={selectedNode.node_name}
              extra={
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Tag color={STATUS_COLOR[selectedNode.status]}>
                    {STATUS_LABEL[selectedNode.status]}
                  </Tag>
                  <Button icon={<ReloadOutlined />} size="small">
                    重启节点
                  </Button>
                </div>
              }
              style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
              bodyStyle={{ flex: 1, overflow: 'auto' }}
            >
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={8}>
                  <Statistic title="节点类型" value={selectedNode.node_type} />
                </Col>
                <Col span={8}>
                  <Statistic title="消息计数" value={selectedNode.message_count} />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="最后心跳"
                    value={formatTime(selectedNode.timestamp)}
                  />
                </Col>
              </Row>

              {selectedNode.last_error && (
                <div
                  style={{
                    backgroundColor: '#fff2f0',
                    border: '1px solid #ffccc7',
                    borderRadius: 4,
                    padding: 12,
                    marginBottom: 16,
                    color: '#cf1322',
                  }}
                >
                  <strong>错误信息：</strong>
                  {selectedNode.last_error}
                </div>
              )}

              <MetricChart
                data={cpuTrendData}
                title="CPU 使用率趋势"
                color="#1677ff"
                unit="%"
              />
            </Card>
          ) : (
            <Card style={{ height: '100%' }}>
              <Empty description="请选择左侧节点查看详情" style={{ marginTop: '20%' }} />
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}
