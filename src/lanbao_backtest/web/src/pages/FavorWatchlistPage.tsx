import React, { useState } from 'react';
import { Card, Table, Button, Tabs, Typography, Space, Tag, message, Popconfirm } from 'antd';
import { EyeOutlined, DeleteOutlined } from '@ant-design/icons';
import { useWatchlist, useRemoveFromWatchlist } from '../hooks/useFavor';

const { Title } = Typography;

const GROUPS = [
  { key: '自选股', label: '自选股' },
  { key: '揽宝', label: '揽宝' },
  { key: '短线', label: '短线' },
];

export const FavorWatchlistPage: React.FC = () => {
  const [activeGroup, setActiveGroup] = useState('自选股');
  const { data, isLoading, refetch } = useWatchlist(undefined, activeGroup);
  const removeMutation = useRemoveFromWatchlist();

  const handleDelete = async (code: string) => {
    try {
      await removeMutation.mutateAsync({ code, group_name: activeGroup });
      message.success('已删除');
    } catch {
      message.error('删除失败');
    }
  };

  const columns = [
    { title: '代码', dataIndex: 'code', key: 'code' },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '来源', dataIndex: 'source_condition', key: 'source_condition' },
    {
      title: '信号',
      dataIndex: 'signal_type',
      key: 'signal_type',
      render: (signal: string) => {
        const color = signal === 'BUY' ? 'green' : signal === 'SELL' ? 'red' : 'default';
        return <Tag color={color}>{signal || 'N/A'}</Tag>;
      },
    },
    { title: '添加时间', dataIndex: 'added_at', key: 'added_at' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space>
          <Popconfirm
            title="确认删除?"
            onConfirm={() => handleDelete(record.code)}
            okText="确认"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />} loading={removeMutation.isPending}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Space style={{ justifyContent: 'space-between', width: '100%' }}>
            <Title level={4} style={{ margin: 0 }}>
              <EyeOutlined /> 自选股管理
            </Title>
            <Button onClick={() => refetch()}>刷新</Button>
          </Space>
        </Card>
        <Card>
          <Tabs activeKey={activeGroup} onChange={setActiveGroup} items={GROUPS} />
          <Table
            dataSource={data?.items || []}
            columns={columns}
            rowKey="code"
            loading={isLoading}
            pagination={{ pageSize: 20 }}
          />
        </Card>
      </Space>
    </div>
  );
};
