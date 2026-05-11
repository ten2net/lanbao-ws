import { useSearchParams, useNavigate } from 'react-router-dom';
import { Card, Button, Empty, Tag, Descriptions, Statistic, Row, Col, Table } from 'antd';
import { ArrowLeftOutlined, BarChartOutlined } from '@ant-design/icons';
import { useBacktestDetail, useBacktestList } from '../hooks/useBacktests';

function formatPct(val: number | null) {
  if (val == null) return '-';
  return `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
}

export function ParamAnalysisPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const backtestId = searchParams.get('backtestId') || undefined;

  const { data: detail, isLoading } = useBacktestDetail(backtestId);
  const { data: listData, isLoading: listLoading } = useBacktestList();

  const meta = detail?.meta ?? {};
  const perf = detail?.performance ?? {};
  const returns = perf.returns ?? {};
  const risk = perf.risk ?? {};
  const tradesPerf = perf.trades ?? {};

  const params = meta.params ?? {};
  const paramEntries = Object.entries(params);

  const listColumns = [
    { title: '回测ID', dataIndex: 'backtest_id', key: 'id' },
    { title: '策略', dataIndex: 'strategy_name', key: 'strategy', render: (v: string, r: any) => v || r.strategy_id },
    { title: '标的', dataIndex: 'symbol', key: 'symbol' },
    {
      title: '总收益',
      dataIndex: 'total_return',
      key: 'total_return',
      render: (v: number | null) => <span style={{ color: (v ?? 0) >= 0 ? '#cf304a' : '#228b22' }}>{formatPct(v)}</span>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Button
          icon={<BarChartOutlined />}
          size="small"
          type="primary"
          onClick={() => navigate(`/param-analysis?backtestId=${record.backtest_id}`)}
        >
          查看分析
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          返回列表
        </Button>
      </div>

      <h2 style={{ marginTop: 0, marginBottom: 16 }}>参数分析</h2>

      {isLoading ? (
        <Card size="small" loading />
      ) : !backtestId ? (
        <Card title="选择要分析的回测" size="small">
          <Table
            columns={listColumns}
            dataSource={listData?.items ?? []}
            rowKey="backtest_id"
            size="small"
            loading={listLoading}
            pagination={false}
          />
        </Card>
      ) : (
        <>
          <Descriptions title={`回测: ${backtestId}`} bordered size="small" style={{ marginBottom: 24 }}>
            <Descriptions.Item label="策略">{meta.strategy_name || meta.strategy_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="标的">{meta.symbol || '-'}</Descriptions.Item>
            <Descriptions.Item label="日期范围">{meta.start_date} ~ {meta.end_date}</Descriptions.Item>
          </Descriptions>

          <Card title="回测参数" size="small" style={{ marginBottom: 24 }}>
            {paramEntries.length === 0 ? (
              <Empty description="该回测没有自定义参数" />
            ) : (
              <Row gutter={[16, 16]}>
                {paramEntries.map(([key, value]) => (
                  <Col key={key} xs={24} sm={12} md={8} lg={6}>
                    <Card size="small" style={{ background: '#fafafa' }}>
                      <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>{key}</div>
                      <div style={{ fontSize: 16, fontWeight: 600 }}>
                        {typeof value === 'number' ? value.toFixed(4) : String(value)}
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
            )}
          </Card>

          <Card title="性能指标" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="总收益" value={formatPct(returns.total_return_pct)} valueStyle={{ color: (returns.total_return_pct ?? 0) >= 0 ? '#cf304a' : '#228b22' }} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="年化收益" value={formatPct(returns.annual_return_pct)} valueStyle={{ color: (returns.annual_return_pct ?? 0) >= 0 ? '#cf304a' : '#228b22' }} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="夏普比率" value={risk.sharpe_ratio != null ? risk.sharpe_ratio.toFixed(2) : '-'} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="最大回撤" value={formatPct(risk.max_drawdown_pct)} valueStyle={{ color: '#228b22' }} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="胜率" value={tradesPerf.win_rate_pct != null ? `${tradesPerf.win_rate_pct.toFixed(1)}%` : '-'} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="交易次数" value={tradesPerf.total_count != null ? String(tradesPerf.total_count) : '-'} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="盈亏比" value={tradesPerf.profit_factor != null ? tradesPerf.profit_factor.toFixed(2) : '-'} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="平均持仓天数" value={tradesPerf.avg_holding_days != null ? tradesPerf.avg_holding_days.toFixed(1) : '-'} />
              </Col>
            </Row>
          </Card>

          <Card title="说明" size="small">
            <p style={{ color: '#666', lineHeight: 1.8 }}>
              参数敏感性分析功能将在后续版本中支持。届时您可以：
            </p>
            <ul style={{ color: '#666', lineHeight: 1.8 }}>
              <li>选择单个参数进行网格扫描，观察不同参数值对收益的影响</li>
              <li>进行二维参数热力图分析，找到最优参数组合</li>
              <li>对比不同参数配置下的回测结果</li>
              <li>导出参数敏感性报告</li>
            </ul>
            <Tag color="blue">敬请期待</Tag>
          </Card>
        </>
      )}
    </div>
  );
}
