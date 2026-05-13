import React from 'react';
import { Card, Progress, Steps, Tag } from 'antd';
import { CheckCircleOutlined, LoadingOutlined, ClockCircleOutlined } from '@ant-design/icons';

interface ResearchProgressProps {
  status: string;
  progress: number;
  message: string;
  currentAgent?: string;
}

const agentSteps = [
  { title: '宏观分析', key: 'macro_analyst' },
  { title: '基本面分析', key: 'fundamental_analyst' },
  { title: '技术面分析', key: 'technical_analyst' },
  { title: '情绪新闻', key: 'sentiment_news_analyst' },
  { title: '投资总监', key: 'portfolio_director' },
];

export const ResearchProgress: React.FC<ResearchProgressProps> = ({
  status,
  progress,
  message,
  currentAgent,
}) => {
  const isRunning = status === 'running';
  const isCompleted = status === 'completed';

  const getCurrentStep = () => {
    if (!currentAgent) return -1;
    return agentSteps.findIndex(s => s.key === currentAgent);
  };

  return (
    <Card title="分析进度" bordered={false}>
      <Progress
        percent={Math.round(progress * 100)}
        status={isCompleted ? 'success' : isRunning ? 'active' : 'normal'}
      />
      <div style={{ marginTop: 16 }}>
        <Tag icon={isRunning ? <LoadingOutlined /> : isCompleted ? <CheckCircleOutlined /> : <ClockCircleOutlined />}>
          {message}
        </Tag>
      </div>
      <Steps
        direction="vertical"
        size="small"
        current={getCurrentStep()}
        items={agentSteps.map(step => ({
          title: step.title,
          icon: getCurrentStep() > agentSteps.indexOf(step) ? <CheckCircleOutlined /> : undefined,
        }))}
        style={{ marginTop: 24 }}
      />
    </Card>
  );
};
