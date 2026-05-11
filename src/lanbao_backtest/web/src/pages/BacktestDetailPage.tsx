import { useParams, useNavigate } from 'react-router-dom';
import { Card, Row, Col, Statistic, Table, Tag, Button, Tabs, Descriptions, Spin } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useBacktestDetail, useEquityCurve, useTrades, useMonthlyReturns } from '../hooks/useBacktests';
import { EquityCurve } from '../components/Charts/EquityCurve';
import { KLineChart } from '../components/Charts/KLineChart';

function formatPct(val: number | null | undefined) {
  if (val == null) return '-';
  return `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
}

function formatNumber(val: number | null | undefined, digits = 2) {
  if (val == null) return '-';
  return val.toFixed(digits);
}

export function BacktestDetailPage() {
  const { backtestId } = useParams<{ backtestId: string }>();
  const navigate = useNavigate();

  const { data: detail, isLoading: detailLoading } = useBacktestDetail(backtestId);
  const { data: equityData, isLoading: equityLoading } = useEquityCurve(backtestId);
  const { data: trades, isLoading: tradesLoading } = useTrades(backtestId);
  const { data: monthly, isLoading: monthlyLoading } = useMonthlyReturns(backtestId);

  const isLoading = detailLoading || equityLoading || tradesLoading || monthlyLoading;

  const perf = detail?.performance ?? {};
  const returns = perf.returns ?? {};
  const risk = perf.risk ?? {};
  const tradesPerf = perf.trades ?? {};
  const meta = detail?.meta ?? {};

  const tradeColumns = [
    { title: '日期', dataIndex: 'trade_date', key: 'trade_date' },
    {
      title: '方向',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => (
        <Tag color={action === 'BUY' ? 'red' : 'green'}>
          {action === 'BUY' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
    { title: '价格', dataIndex: 'price', key: 'price', render: (v: number) => v.toFixed(2) },
    { title: '金额', dataIndex: 'amount', key: 'amount', render: (v: number) => v.toFixed(2) },
    {
      title: '盈亏',
      dataIndex: 'pnl',
      key: 'pnl',
      render: (v: number | null) => {
        if (v == null) return '-';
        return (
          <span style={{ color: v >= 0 ? '#cf304a' : '#228b22', fontWeight: 600 }}>
            {v >= 0 ? '+' : ''}{v.toFixed(2)}
          </span>
        );
      },
    },
  ];

  const monthlyYears = monthly ? Object.keys(monthly).sort() : [];
  const months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'];

  const klineData = equityData
    ? equityData.map((d) => ({
        time: d.date,
        open: d.equity * 0.998,
        high: d.equity * 1.002,
        low: d.equity * 0.997,
        close: d.equity,
      }))
    : [];

  const tradeMarkers = trades
    ? trades.map((t) => ({
        time: t.trade_date,
        position: (t.action === 'BUY' ? 'belowBar' : 'aboveBar') as 'belowBar' | 'aboveBar',
        color: t.action === 'BUY' ? '#cf304a' : '#228b22',
        shape: (t.action === 'BUY' ? 'arrowUp' : 'arrowDown') as 'arrowUp' | 'arrowDown',
        text: t.action === 'BUY' ? '买' : '卖',
      }))
    : [];

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          返回列表
        </Button>
      </div>

      <Descriptions title={`回测详情: ${backtestId}`} bordered size="small" style={{ marginBottom: 24 }}>
        <Descriptions.Item label="策略">{meta.strategy_name || meta.strategy_id || '-'}</Descriptions.Item>
        <Descriptions.Item label="标的">{meta.symbol || '-'}</Descriptions.Item>
        <Descriptions.Item label="日期范围">{meta.start_date} ~ {meta.end_date}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={meta.status === 'completed' ? 'success' : 'default'}>
            {meta.status === 'completed' ? '已完成' : meta.status || '未知'}
          </Tag>
        </Descriptions.Item>
      </Descriptions>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic title="总收益" value={formatPct(returns.total_return_pct)} valueStyle={{ color: (returns.total_return_pct ?? 0) >= 0 ? '#cf304a' : '#228b22' }} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic title="年化收益" value={formatPct(returns.annual_return_pct)} valueStyle={{ color: (returns.annual_return_pct ?? 0) >= 0 ? '#cf304a' : '#228b22' }} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic title="夏普比率" value={formatNumber(risk.sharpe_ratio)} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic title="最大回撤" value={formatPct(risk.max_drawdown_pct)} valueStyle={{ color: '#228b22' }} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic title="胜率" value={tradesPerf.win_rate_pct != null ? `${tradesPerf.win_rate_pct.toFixed(1)}%` : '-'} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic title="交易次数" value={formatNumber(tradesPerf.total_count, 0)} />
          </Card>
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="equity"
        items={[
          {
            key: 'equity',
            label: '权益曲线',
            children: (
              <Card title="权益曲线" size="small">
                <EquityCurve data={equityData ?? []} showDrawdown />
              </Card>
            ),
          },
          {
            key: 'kline',
            label: 'K线交易图',
            children: (
              <Card title="K线与交易标记" size="small">
                <KLineChart data={klineData} trades={tradeMarkers} />
              </Card>
            ),
          },
          {
            key: 'trades',
            label: '交易记录',
            children: (
              <Card title="交易明细" size="small">
                <Table
                  columns={tradeColumns}
                  dataSource={trades ?? []}
                  rowKey="trade_id"
                  size="small"
                  pagination={{ pageSize: 20 }}
                  scroll={{ x: 800 }}
                />
              </Card>
            ),
          },
          {
            key: 'monthly',
            label: '月度收益',
            children: (
              <Card title="月度收益矩阵" size="small">
                {monthlyLoading ? (
                  <Spin />
                ) : monthlyYears.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr>
                        <th style={{ border: '1px solid #e8e8e8', padding: '8px 12px', background: '#fafafa' }}>年份</th>
                        {months.map((m) => (
                          <th key={m} style={{ border: '1px solid #e8e8e8', padding: '8px 4px', background: '#fafafa', textAlign: 'center', minWidth: 50 }}>{m}</th>
                        ))}
                        <th style={{ border: '1px solid #e8e8e8', padding: '8px 12px', background: '#fafafa' }}>年度</th>
                      </tr>
                    </thead>
                    <tbody>
                      {monthlyYears.map((year) => {
                        const yearData = monthly![year];
                        const yearTotal = Object.values(yearData).reduce((a, b) => a + (b || 0), 0);
                        return (
                          <tr key={year}>
                            <td style={{ border: '1px solid #e8e8e8', padding: '8px 12px', fontWeight: 600 }}>{year}</td>
                            {months.map((m) => {
                              const val = yearData[m];
                              const bg = val == null ? '#f5f5f5' : val >= 0 ? 'rgba(207,48,74,0.1)' : 'rgba(34,139,34,0.1)';
                              return (
                                <td key={m} style={{ border: '1px solid #e8e8e8', padding: '8px 4px', textAlign: 'center', background: bg, color: val == null ? '#999' : val >= 0 ? '#cf304a' : '#228b22' }}>
                                  {val != null ? `${val.toFixed(1)}%` : '-'}
                                </td>
                              );
                            })}
                            <td style={{ border: '1px solid #e8e8e8', padding: '8px 12px', fontWeight: 600, textAlign: 'center', color: yearTotal >= 0 ? '#cf304a' : '#228b22' }}>
                              {yearTotal.toFixed(1)}%
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
