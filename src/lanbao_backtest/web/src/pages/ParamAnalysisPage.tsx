import { useSearchParams, useNavigate } from 'react-router-dom';
import { Card, Button, Empty, Tag, Descriptions, Statistic, Row, Col } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useBacktestDetail } from '../hooks/useBacktests';

function formatPct(val: number | null) {
  if (val == null) return '-';
  return `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
}

export function ParamAnalysisPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const backtestId = searchParams.get('backtestId') || undefined;

  const { data: detail, isLoading } = useBacktestDetail(backtestId);

  const meta = detail?.meta ?? {};
  const perf = detail?.performance ?? {};

  const params = meta.params ?? {};
  const paramEntries = Object.entries(params);

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
        <Empty description="未指定回测ID" style={{ marginTop: 40 }} />
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
                <Statistic title="总收益" value={formatPct(perf.total_return)} valueStyle={{ color: (perf.total_return ?? 0) >= 0 ? '#cf304a' : '#228b22' }} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="年化收益" value={formatPct(perf.annual_return)} valueStyle={{ color: (perf.annual_return ?? 0) >= 0 ? '#cf304a' : '#228b22' }} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="夏普比率" value={perf.sharpe_ratio != null ? perf.sharpe_ratio.toFixed(2) : '-'} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="最大回撤" value={formatPct(perf.max_drawdown)} valueStyle={{ color: '#228b22' }} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="胜率" value={perf.win_rate != null ? `${(perf.win_rate * 100).toFixed(1)}%` : '-'} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="交易次数" value={perf.trade_count != null ? String(perf.trade_count) : '-'} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="盈亏比" value={perf.profit_factor != null ? perf.profit_factor.toFixed(2) : '-'} />
              </Col>
              <Col xs={12} sm={8} md={6} lg={4}>
                <Statistic title="平均持仓天数" value={perf.avg_holding_days != null ? perf.avg_holding_days.toFixed(1) : '-'} />
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
