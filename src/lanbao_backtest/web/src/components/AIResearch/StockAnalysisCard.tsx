import React from 'react';
import { Card, Space, Tag, Row, Col, Divider, Tooltip } from 'antd';
import {
  FundOutlined,
  LineChartOutlined,
  SmileOutlined,
  FileTextOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
} from '@ant-design/icons';

const VERDICT_COLOR: Record<string, string> = {
  STRONG_BUY: 'green',
  BUY: 'green',
  HOLD: 'default',
  SELL: 'red',
  STRONG_SELL: 'red',
};

const VerdictTag: React.FC<{ verdict?: string }> = ({ verdict }) => {
  if (!verdict) return null;
  const color = VERDICT_COLOR[verdict] || 'default';
  const icon =
    verdict === 'BUY' || verdict === 'STRONG_BUY' ? (
      <ArrowUpOutlined />
    ) : verdict === 'SELL' || verdict === 'STRONG_SELL' ? (
      <ArrowDownOutlined />
    ) : (
      <MinusOutlined />
    );
  return (
    <Tag color={color} icon={icon}>
      {verdict}
    </Tag>
  );
};

const ScoreBar: React.FC<{ score?: number }> = ({ score }) => {
  if (score === undefined || score === null) return null;
  const color = score >= 70 ? 'green' : score >= 50 ? 'orange' : 'red';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div
        style={{
          width: 100,
          height: 8,
          background: '#f0f0f0',
          borderRadius: 4,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${score}%`,
            height: '100%',
            background: color,
            borderRadius: 4,
            transition: 'width 0.5s',
          }}
        />
      </div>
      <span style={{ fontWeight: 'bold', color }}>{score}分</span>
    </div>
  );
};

interface AgentReportProps {
  title: string;
  icon: React.ReactNode;
  verdict?: string;
  score?: number;
  details?: Record<string, any>;
  raw?: string;
  bullCase?: string[];
  bearCase?: string[];
}

const AgentReportCard: React.FC<AgentReportProps> = ({
  title,
  icon,
  verdict,
  score,
  details,
  raw,
  bullCase,
  bearCase,
}) => {
  return (
    <Card
      size="small"
      title={
        <Space>
          {icon}
          <strong>{title}</strong>
          <VerdictTag verdict={verdict} />
          <ScoreBar score={score} />
        </Space>
      }
      style={{ marginBottom: 12 }}
    >
      {details && (
        <div style={{ fontSize: 13, color: '#666' }}>
          {Object.entries(details).map(([k, v]) => (
            <div key={k}>
              {k}: <strong>{v !== null && v !== undefined ? String(v) : '—'}</strong>
            </div>
          ))}
        </div>
      )}
      {bullCase && bullCase.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ color: 'green', fontWeight: 'bold', fontSize: 12 }}>看多理由</div>
          {bullCase.map((r, i) => (
            <div key={i} style={{ fontSize: 13, color: '#333' }}>
              • {r}
            </div>
          ))}
        </div>
      )}
      {bearCase && bearCase.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ color: 'red', fontWeight: 'bold', fontSize: 12 }}>看空理由</div>
          {bearCase.map((r, i) => (
            <div key={i} style={{ fontSize: 13, color: '#333' }}>
              • {r}
            </div>
          ))}
        </div>
      )}
      {raw && (
        <Tooltip title={raw}>
          <div
            style={{
              marginTop: 8,
              fontSize: 12,
              color: '#999',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            <FileTextOutlined /> {raw.slice(0, 60)}...
          </div>
        </Tooltip>
      )}
    </Card>
  );
};

interface StockAnalysisCardProps {
  symbol: string;
  name?: string;
  synthesis?: any;
  fundamental?: any;
  technical?: any;
  sentiment?: any;
}

export const StockAnalysisCard: React.FC<StockAnalysisCardProps> = ({
  symbol,
  name,
  synthesis,
  fundamental,
  technical,
  sentiment,
}) => {
  // 计算 Agent 间分歧
  const verdicts: { label: string; verdict: string }[] = [];
  if (fundamental?.verdict) verdicts.push({ label: '基本面', verdict: fundamental.verdict });
  if (technical?.verdict) verdicts.push({ label: '技术面', verdict: technical.verdict });
  if (sentiment?.verdict) verdicts.push({ label: '情绪面', verdict: sentiment.verdict });

  const buyCount = verdicts.filter((v) => v.verdict === 'BUY' || v.verdict === 'STRONG_BUY').length;
  const sellCount = verdicts.filter((v) => v.verdict === 'SELL' || v.verdict === 'STRONG_SELL').length;

  const hasDisagreement = buyCount > 0 && sellCount > 0;

  return (
    <Card
      title={
        <Space>
          <strong>
            {symbol} {name}
          </strong>
          {synthesis?.verdict && <VerdictTag verdict={synthesis.verdict} />}
          {synthesis?.score !== undefined && <ScoreBar score={synthesis.score} />}
        </Space>
      }
    >
      {/* 综合判断 */}
      {synthesis && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 'bold', marginBottom: 8 }}>投资总监综合判断</div>
          <Row gutter={16}>
            <Col span={8}>
              <div style={{ color: '#666', fontSize: 12 }}>评级</div>
              <VerdictTag verdict={synthesis.verdict} />
            </Col>
            <Col span={8}>
              <div style={{ color: '#666', fontSize: 12 }}>得分</div>
              <ScoreBar score={synthesis.score} />
            </Col>
            <Col span={8}>
              <div style={{ color: '#666', fontSize: 12 }}>建议仓位</div>
              <strong>{synthesis.position_suggestion || '—'}</strong>
            </Col>
          </Row>
          {synthesis.bull_case && synthesis.bull_case.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ color: 'green', fontWeight: 'bold', fontSize: 12 }}>看多理由</div>
              {synthesis.bull_case.map((r: string, i: number) => (
                <div key={i} style={{ fontSize: 13 }}>• {r}</div>
              ))}
            </div>
          )}
          {synthesis.bear_case && synthesis.bear_case.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ color: 'red', fontWeight: 'bold', fontSize: 12 }}>看空理由</div>
              {synthesis.bear_case.map((r: string, i: number) => (
                <div key={i} style={{ fontSize: 13 }}>• {r}</div>
              ))}
            </div>
          )}
          {synthesis.risk_notes && synthesis.risk_notes.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ color: 'orange', fontWeight: 'bold', fontSize: 12 }}>风险提示</div>
              {synthesis.risk_notes.map((r: string, i: number) => (
                <div key={i} style={{ fontSize: 13 }}>• {r}</div>
              ))}
            </div>
          )}
        </div>
      )}

      <Divider style={{ margin: '12px 0' }} />

      {/* Agent 间分歧提示 */}
      {hasDisagreement && (
        <div
          style={{
            background: '#fff2f0',
            border: '1px solid #ffccc7',
            borderRadius: 4,
            padding: '8px 12px',
            marginBottom: 12,
            fontSize: 13,
          }}
        >
          <strong>Agent 间存在分歧：</strong>
          {verdicts.map((v) => (
            <Tag
              key={v.label}
              color={
                v.verdict === 'BUY' || v.verdict === 'STRONG_BUY'
                  ? 'green'
                  : v.verdict === 'SELL' || v.verdict === 'STRONG_SELL'
                    ? 'red'
                    : 'default'
              }
              style={{ marginLeft: 8 }}
            >
              {v.label}: {v.verdict}
            </Tag>
          ))}
        </div>
      )}

      {/* 各 Agent 独立分析 */}
      <div style={{ fontWeight: 'bold', marginBottom: 12 }}>各维度独立分析</div>

      {fundamental && (
        <AgentReportCard
          title="基本面分析"
          icon={<FundOutlined />}
          verdict={fundamental.verdict}
          score={fundamental.score}
          details={{
            'PE(TTM)': fundamental.pe_ttm,
            PB: fundamental.pb,
            ROE: fundamental.roe,
            '负债率': fundamental.debt_ratio,
            '营收增长': fundamental.revenue_growth,
            '利润增长': fundamental.profit_growth,
          }}
          bullCase={fundamental.key_points}
          bearCase={fundamental.concerns}
          raw={fundamental.raw_analysis}
        />
      )}

      {technical && (
        <AgentReportCard
          title="技术面分析"
          icon={<LineChartOutlined />}
          verdict={technical.verdict}
          score={technical.score}
          details={{
            趋势: technical.trend,
            支撑位: technical.support,
            压力位: technical.resistance,
            形态: technical.patterns?.join(', ') || '—',
            信号: technical.signals?.join(', ') || '—',
          }}
          raw={technical.raw_analysis}
        />
      )}

      {sentiment && (
        <AgentReportCard
          title="情绪面分析"
          icon={<SmileOutlined />}
          verdict={sentiment.verdict}
          score={sentiment.score}
          details={{
            '情绪得分': sentiment.sentiment_score,
            '新闻摘要': sentiment.news_summary,
            '资金流向': sentiment.capital_trend,
            '热度': sentiment.hot_degree,
          }}
          raw={sentiment.raw_analysis}
        />
      )}
    </Card>
  );
};
