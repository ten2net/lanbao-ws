import React, { useState } from 'react';
import { Card, Button, Table, Typography, message, Space } from 'antd';
import { FileTextOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useResearchReports, useTriggerMarketDaily } from '../hooks/useResearch';

const { Title } = Typography;

export const AIResearchDailyPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: reportsData, isLoading } = useResearchReports({ limit: 50 });
  const triggerDaily = useTriggerMarketDaily();
  const [generating, setGenerating] = useState(false);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const result = await triggerDaily.mutateAsync(undefined);
      message.success(`已开始生成日报: ${result.report_id}`);
      navigate(`/ai-research/stock?reportId=${result.report_id}`);
    } catch (e) {
      message.error('生成日报失败');
    } finally {
      setGenerating(false);
    }
  };

  const columns = [
    { title: '日期', dataIndex: 'created_at', key: 'date' },
    { title: '报告ID', dataIndex: 'report_id', key: 'report_id',
      render: (id: string) => (
        <Button type="link" onClick={() => navigate(`/ai-research/history?reportId=${id}`)}>{id}</Button>
      ),
    },
    { title: '操作', key: 'action',
      render: (_: any, record: any) => (
        <Button size="small" onClick={() => navigate(`/ai-research/history?reportId=${record.report_id}`)}>查看</Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Space style={{ justifyContent: 'space-between', width: '100%' }}>
            <Title level={4} style={{ margin: 0 }}><FileTextOutlined /> 市场日报</Title>
            <Button type="primary" icon={<ReloadOutlined />} loading={generating} onClick={handleGenerate}>
              生成今日报告
            </Button>
          </Space>
        </Card>
        <Card title="历史日报" loading={isLoading}>
          <Table dataSource={reportsData?.reports || []} columns={columns} rowKey="report_id" pagination={{ pageSize: 10 }} />
        </Card>
      </Space>
    </div>
  );
};
