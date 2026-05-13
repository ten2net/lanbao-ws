import React, { useState } from 'react';
import { Card, Table, Button, Typography } from 'antd';
import { HistoryOutlined, EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useResearchReports } from '../hooks/useResearch';

const { Title } = Typography;

export const AIResearchHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const { data, isLoading } = useResearchReports({ limit: pageSize, offset: (page - 1) * pageSize });

  const columns = [
    { title: '报告ID', dataIndex: 'report_id', key: 'report_id' },
    { title: '生成日期', dataIndex: 'created_at', key: 'created_at' },
    { title: '操作', key: 'action',
      render: (_: any, record: any) => (
        <Button size="small" icon={<EyeOutlined />}
          onClick={() => navigate(`/ai-research/stock?reportId=${record.report_id}`)}>查看</Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Title level={4}><HistoryOutlined /> 报告历史</Title>
        <Table dataSource={data?.reports || []} columns={columns} rowKey="report_id" loading={isLoading}
          pagination={{ current: page, pageSize, total: data?.total || 0, onChange: setPage }} />
      </Card>
    </div>
  );
};
