import React, { useState } from 'react';
import { Card, Table, Button, Tabs, Typography, Space, Tag, message, Popconfirm, Select, Alert, Spin, Popover } from 'antd';
import { EyeOutlined, DeleteOutlined, SyncOutlined, CloudOutlined } from '@ant-design/icons';
import { useWatchlist, useRemoveFromWatchlist, useEastMoneyWatchlist, useEastMoneyGroups, useSyncToEastMoney, useKLineData } from '../hooks/useFavor';
import { StockMiniChart } from '../components/Charts/StockMiniChart';

const { Title } = Typography;

const LOCAL_GROUPS = [
  { key: '自选股', label: '自选股' },
  { key: '揽宝', label: '揽宝' },
  { key: '短线', label: '短线' },
];

/** K线悬浮预览组件 */
const StockKLinePopover: React.FC<{ symbol: string; name?: string; children: React.ReactNode }> = ({ symbol, name, children }) => {
  const [open, setOpen] = useState(false);
  const { data: klineData, isLoading, refetch } = useKLineData(open ? symbol : undefined, 30);

  const titleText = name ? `${name} (${symbol})` : symbol;

  const content = (
    <div style={{ width: 380 }}>
      <div style={{ fontWeight: 'bold', marginBottom: 8, fontSize: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{titleText} 近30日K线</span>
        <span style={{ fontSize: 12, fontWeight: 'normal', color: '#666' }}>
          {klineData?.has_today ? (
            <span style={{ color: '#52c41a' }}>● 含今日</span>
          ) : klineData ? (
            <span style={{ color: '#faad14' }}>● 无今日</span>
          ) : null}
        </span>
      </div>
      {isLoading ? (
        <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin size="small" />
        </div>
      ) : klineData && klineData.data.length > 0 ? (
        <StockMiniChart data={klineData.data} width={380} />
      ) : (
        <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
          暂无K线数据
        </div>
      )}
      {klineData?.today_debug && (
        <div style={{ marginTop: 8, padding: '4px 8px', background: '#fff2f0', border: '1px solid #ffccc7', borderRadius: 4, fontSize: 12, color: '#cf1322' }}>
          <strong>调试:</strong> {klineData.today_debug}
        </div>
      )}
    </div>
  );

  return (
    <Popover
      content={content}
      title={null}
      open={open}
      onOpenChange={(visible) => {
        setOpen(visible);
        if (visible) refetch();
      }}
      trigger="hover"
      placement="right"
      mouseEnterDelay={0.3}
      mouseLeaveDelay={0.1}
    >
      {children}
    </Popover>
  );
};

export const FavorWatchlistPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('local');
  const [activeGroup, setActiveGroup] = useState('自选股');
  const [emGroup, setEmGroup] = useState('自选股');

  // 本地自选股
  const { data: localData, isLoading: localLoading, refetch: refetchLocal } = useWatchlist(undefined, activeGroup);
  const removeMutation = useRemoveFromWatchlist();

  // EastMoney 自选股
  const { data: emData, isLoading: emLoading, refetch: refetchEm } = useEastMoneyWatchlist(emGroup);
  const { data: emGroupsData } = useEastMoneyGroups();
  const syncMutation = useSyncToEastMoney();

  const handleDelete = async (code: string) => {
    try {
      await removeMutation.mutateAsync({ code, group_name: activeGroup });
      message.success('已删除');
    } catch {
      message.error('删除失败');
    }
  };

  const handleSync = async () => {
    try {
      await syncMutation.mutateAsync({ sys_group: '揽宝', em_group: emGroup });
    } catch {
      // error handled by hook
    }
  };

  const localColumns = [
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      render: (code: string, record: any) => (
        <StockKLinePopover symbol={code} name={record.name}>
          <span style={{ cursor: 'pointer', color: '#1677ff', fontWeight: 500 }}>{code}</span>
        </StockKLinePopover>
      ),
    },
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

  const emColumns = [
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      width: 90,
      render: (code: string, record: any) => (
        <StockKLinePopover symbol={code} name={record.name}>
          <span style={{ cursor: 'pointer', color: '#1677ff', fontWeight: 500 }}>{code}</span>
        </StockKLinePopover>
      ),
    },
    { title: '名称', dataIndex: 'name', key: 'name', width: 120 },
    {
      title: '最新价',
      dataIndex: 'price',
      key: 'price',
      width: 90,
      align: 'right' as const,
      render: (price: number) => price ? price.toFixed(2) : '-',
    },
    {
      title: '涨跌额',
      dataIndex: 'change',
      key: 'change',
      width: 90,
      align: 'right' as const,
      render: (change: number) => {
        if (!change && change !== 0) return '-';
        const color = change > 0 ? '#cf1322' : change < 0 ? '#3f8600' : '#666';
        return <span style={{ color }}>{change > 0 ? '+' : ''}{change.toFixed(2)}</span>;
      },
    },
    {
      title: '涨跌幅',
      dataIndex: 'change_pct',
      key: 'change_pct',
      width: 90,
      align: 'right' as const,
      render: (pct: number) => {
        if (!pct && pct !== 0) return '-';
        const color = pct > 0 ? '#cf1322' : pct < 0 ? '#3f8600' : '#666';
        return <span style={{ color }}>{pct > 0 ? '+' : ''}{pct.toFixed(2)}%</span>;
      },
    },
    {
      title: '最高',
      dataIndex: 'high',
      key: 'high',
      width: 90,
      align: 'right' as const,
      render: (high: number) => high ? high.toFixed(2) : '-',
    },
    {
      title: '最低',
      dataIndex: 'low',
      key: 'low',
      width: 90,
      align: 'right' as const,
      render: (low: number) => low ? low.toFixed(2) : '-',
    },
  ];

  const emGroupOptions = emGroupsData?.groups.map((g: any) => ({ label: g.name, value: g.name })) || [];

  const tabItems = [
    {
      key: 'local',
      label: '系统自选股',
      children: (
        <>
          <Tabs
            activeKey={activeGroup}
            onChange={setActiveGroup}
            items={LOCAL_GROUPS.map(g => ({ key: g.key, label: g.label }))}
            style={{ marginBottom: 16 }}
          />
          <Table
            dataSource={localData?.items || []}
            columns={localColumns}
            rowKey="code"
            loading={localLoading}
            pagination={{ pageSize: 20 }}
          />
        </>
      ),
    },
    {
      key: 'eastmoney',
      label: (
        <span>
          <CloudOutlined /> 东方财富
        </span>
      ),
      children: (
        <>
          <Space style={{ marginBottom: 16 }}>
            <span>分组:</span>
            <Select
              value={emGroup}
              onChange={setEmGroup}
              options={emGroupOptions.length > 0 ? emGroupOptions : [{ label: '自选股', value: '自选股' }]}
              style={{ width: 160 }}
            />
            <Button icon={<SyncOutlined />} onClick={() => refetchEm()} loading={emLoading}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<SyncOutlined spin={syncMutation.isPending} />}
              onClick={handleSync}
              loading={syncMutation.isPending}
            >
              同步到东方财富
            </Button>
          </Space>

          {emData?.items === undefined && !emLoading && (
            <Alert
              message="无法获取东方财富自选股"
              description="请确保 EastMoney 凭证已配置（EASTMONEY_APPKEY 和 EASTMONEY_COOKIE），且 favor_node 已启动。"
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          <Spin spinning={emLoading}>
            <Table
              dataSource={emData?.items || []}
              columns={emColumns}
              rowKey="code"
              pagination={{ pageSize: 20 }}
              locale={{ emptyText: emLoading ? '加载中...' : '该分组下无自选股' }}
              scroll={{ x: 'max-content' }}
            />
          </Spin>
        </>
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
            <Button onClick={() => {
              if (activeTab === 'local') refetchLocal();
              else refetchEm();
            }}>
              刷新
            </Button>
          </Space>
        </Card>
        <Card>
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
        </Card>
      </Space>
    </div>
  );
};
