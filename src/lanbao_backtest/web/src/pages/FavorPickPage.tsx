import React, { useState, useEffect } from 'react';
import {
  Card, Button, Checkbox, Typography, Space, Tag, message, Divider, Spin,
} from 'antd';
import { PlayCircleOutlined, FilterOutlined } from '@ant-design/icons';
import { useConditions, usePick } from '../hooks/useFavor';

const { Title, Text } = Typography;

export const FavorPickPage: React.FC = () => {
  const { data: conditionsData, isLoading: conditionsLoading } = useConditions();
  const pickMutation = usePick();
  const [selectedConditions, setSelectedConditions] = useState<string[]>([]);
  const [clearExisting, setClearExisting] = useState(false);

  const conditions = conditionsData?.conditions || [];
  const enabledConditions = conditions.filter((c) => c.enabled);

  useEffect(() => {
    if (enabledConditions.length > 0) {
      setSelectedConditions(enabledConditions.map((c) => c.name));
    }
  }, [conditionsData]);

  const handlePick = async () => {
    if (selectedConditions.length === 0) {
      message.warning('请至少选择一个条件');
      return;
    }
    try {
      const result = await pickMutation.mutateAsync({
        condition_names: selectedConditions,
        clear_existing: clearExisting,
      });
      message.success(`选股完成: ${result.message}`);
    } catch {
      message.error('选股失败');
    }
  };

  const result = pickMutation.data;

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Space style={{ justifyContent: 'space-between', width: '100%' }}>
            <Title level={4} style={{ margin: 0 }}>
              <FilterOutlined /> 智能选股
            </Title>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handlePick}
              loading={pickMutation.isPending}
            >
              开始选股
            </Button>
          </Space>
        </Card>

        <Card title="选择条件">
          <Spin spinning={conditionsLoading}>
            <Checkbox.Group
              value={selectedConditions}
              onChange={(vals) => setSelectedConditions(vals as string[])}
            >
              <Space direction="vertical">
                {conditions.map((c) => (
                  <Checkbox key={c.name} value={c.name} disabled={!c.enabled}>
                    {c.name}
                    {c.enabled ? null : <Tag style={{ marginLeft: 8 }}>已禁用</Tag>}
                  </Checkbox>
                ))}
              </Space>
            </Checkbox.Group>
          </Spin>
          <Divider />
          <Checkbox checked={clearExisting} onChange={(e) => setClearExisting(e.target.checked)}>
            清空现有自选股
          </Checkbox>
        </Card>

        {result && (
          <Card title="选股结果">
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Space size="large">
                <Text>总计: <strong>{result.total_unique}</strong></Text>
                <Text>新增: <strong style={{ color: '#3f8600' }}>{result.added}</strong></Text>
                <Text>已存在: <strong style={{ color: '#faad14' }}>{result.existing}</strong></Text>
              </Space>
              <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', padding: 12, borderRadius: 4 }}>
                <Text type="secondary">
                  新增股票已保存到<strong>系统自选股 → 揽宝</strong>分组。
                  {result.existing > 0 && ' 已存在表示这些股票已在系统自选股中，本次未重复添加。'}
                </Text>
              </div>
              <div>
                {result.codes.map((code) => (
                  <Tag key={code} style={{ marginBottom: 4 }}>{code}</Tag>
                ))}
              </div>
            </Space>
          </Card>
        )}
      </Space>
    </div>
  );
};
