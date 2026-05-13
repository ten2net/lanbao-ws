import React from 'react';
import { Card, Tag, Row, Col, Statistic, List, Typography } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

interface StockAnalysisCardProps {
  symbol: string;
  name?: string;
  synthesis?: {
    verdict: string;
    score: number;
    bull_case: string[];
    bear_case: string[];
    position_suggestion: string;
    risk_notes: string[];
  };
}

const verdictColors: Record<string, string> = {
  STRONG_BUY: 'green', BUY: 'cyan', HOLD: 'blue', SELL: 'orange', STRONG_SELL: 'red',
};

const verdictLabels: Record<string, string> = {
  STRONG_BUY: '强力买入', BUY: '买入', HOLD: '持有', SELL: '卖出', STRONG_SELL: '强力卖出',
};

export const StockAnalysisCard: React.FC<StockAnalysisCardProps> = ({
  symbol, name, synthesis,
}) => {
  if (!synthesis) {
    return (
      <Card title={`${symbol} ${name || ''}`} size="small">
        <Typography.Text type="secondary">分析数据不可用</Typography.Text>
      </Card>
    );
  }

  return (
    <Card
      title={
        <span>
          {symbol} {name}
          <Tag color={verdictColors[synthesis.verdict]} style={{ marginLeft: 8 }}>
            {verdictLabels[synthesis.verdict] || synthesis.verdict}
          </Tag>
        </span>
      }
      size="small"
    >
      <Row gutter={16}>
        <Col span={8}>
          <Statistic title="综合得分" value={synthesis.score} suffix="/100"
            valueStyle={{ color: synthesis.score >= 70 ? '#3f8600' : synthesis.score >= 50 ? '#1890ff' : '#cf1322' }}
          />
        </Col>
        <Col span={8}>
          <Statistic title="仓位建议" value={synthesis.position_suggestion} />
        </Col>
        <Col span={8}>
          <div>
            <Typography.Text type="secondary">风险:</Typography.Text>
            <div>{synthesis.risk_notes.map((note, i) => (
              <Tag key={i} color="warning" style={{ marginTop: 4 }}>{note}</Tag>
            ))}</div>
          </div>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Typography.Title level={5}><ArrowUpOutlined style={{ color: 'green' }} /> 看多理由</Typography.Title>
          <List size="small" dataSource={synthesis.bull_case}
            renderItem={(item) => <List.Item>{item}</List.Item>} />
        </Col>
        <Col span={12}>
          <Typography.Title level={5}><ArrowDownOutlined style={{ color: 'red' }} /> 看空理由</Typography.Title>
          <List size="small" dataSource={synthesis.bear_case}
            renderItem={(item) => <List.Item>{item}</List.Item>} />
        </Col>
      </Row>
    </Card>
  );
};
