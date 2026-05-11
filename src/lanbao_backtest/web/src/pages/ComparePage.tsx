import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Button, Select, Space, Table, Statistic, Row, Col, Empty } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useBacktestList } from '../hooks/useBacktests';
import { EquityCurve } from '../components/Charts/EquityCurve';
import { useEquityCurve } from '../hooks/useBacktests';

const { Option } = Select;

function formatPct(val: number | null) {
  if (val == null) return '-';
  return `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
}

export function ComparePage() {
  const navigate = useNavigate();
  const { data: listData } = useBacktestList();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const items = listData?.items ?? [];

  const compareColumns = [
    { title: '回测ID', dataIndex: 'backtest_id', key: 'id' },
    { title: '策略', dataIndex: 'strategy_name', key: 'strategy', render: (v: string, r: any) => v || r.strategy_id },
    { title: '标的', dataIndex: 'symbol', key: 'symbol' },
    {
      title: '总收益',
      dataIndex: 'total_return',
      key: 'total_return',
      render: (v: number | null) => <span style={{ color: (v ?? 0) >= 0 ? '#cf304a' : '#228b22', fontWeight: 600 }}>{formatPct(v)}</span>,
    },
    {
      title: '年化收益',
      dataIndex: 'annual_return',
      key: 'annual_return',
      render: (v: number | null) => <span style={{ color: (v ?? 0) >= 0 ? '#cf304a' : '#228b22' }}>{formatPct(v)}</span>,
    },
    {
      title: '夏普比率',
      dataIndex: 'sharpe_ratio',
      key: 'sharpe_ratio',
      render: (v: number | null) => v != null ? v.toFixed(2) : '-',
    },
    {
      title: '最大回撤',
      dataIndex: 'max_drawdown',
      key: 'max_drawdown',
      render: (v: number | null) => <span style={{ color: '#228b22' }}>{formatPct(v)}</span>,
    },
    {
      title: '胜率',
      dataIndex: 'win_rate',
      key: 'win_rate',
      render: (v: number | null) => v != null ? `${v.toFixed(1)}%` : '-',
    },
    {
      title: '交易次数',
      dataIndex: 'trade_count',
      key: 'trade_count',
    },
  ];

  const selectedItems = items.filter((i) => selectedIds.includes(i.backtest_id));

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>返回列表</Button>
          <span style={{ fontSize: 16, fontWeight: 600 }}>批量对比</span>
        </Space>
      </div>

      <Card title="选择回测" size="small" style={{ marginBottom: 16 }}>
        <Select
          mode="multiple"
          placeholder="选择要对比的回测（最多6个）"
          style={{ width: '100%' }}
          value={selectedIds}
          onChange={(vals) => setSelectedIds(vals.slice(0, 6))}
          maxTagCount={6}
        >
          {items.map((item) => (
            <Option key={item.backtest_id} value={item.backtest_id}>
              {item.backtest_id} | {item.strategy_name || item.strategy_id} | {item.symbol}
            </Option>
          ))}
        </Select>
      </Card>

      {selectedItems.length > 0 ? (
        <>
          <Card title="对比表格" size="small" style={{ marginBottom: 16 }}>
            <Table
              columns={compareColumns}
              dataSource={selectedItems}
              rowKey="backtest_id"
              size="small"
              pagination={false}
              scroll={{ x: 1000 }}
            />
          </Card>

          <Card title="权益曲线对比" size="small" style={{ marginBottom: 16 }}>
            <CompareEquityCharts ids={selectedIds} />
          </Card>

          <Row gutter={[16, 16]}>
            {selectedItems.map((item) => (
              <Col key={item.backtest_id} xs={24} sm={12} md={8} lg={6}>
                <Card size="small" title={item.backtest_id}>
                  <Statistic title="总收益" value={formatPct(item.total_return)} valueStyle={{ fontSize: 18, color: (item.total_return ?? 0) >= 0 ? '#cf304a' : '#228b22' }} />
                  <Statistic title="夏普比率" value={item.sharpe_ratio != null ? item.sharpe_ratio.toFixed(2) : '-'} valueStyle={{ fontSize: 14 }} />
                </Card>
              </Col>
            ))}
          </Row>
        </>
      ) : (
        <Empty description="请选择至少一个回测进行对比" style={{ marginTop: 40 }} />
      )}
    </div>
  );
}

function CompareEquityCharts({ ids }: { ids: string[] }) {
  const [activeId, setActiveId] = useState<string>(ids[0]);
  const { data } = useEquityCurve(activeId);

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        {ids.map((id) => (
          <Button key={id} size="small" type={id === activeId ? 'primary' : 'default'} onClick={() => setActiveId(id)}>
            {id}
          </Button>
        ))}
      </Space>
      <EquityCurve data={data ?? []} />
    </div>
  );
}
