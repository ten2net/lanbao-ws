import React, { useState } from 'react';
import {
  Card, Table, Button, Typography, Space, Switch, Modal, Form, Input, InputNumber, message, Popconfirm,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SettingOutlined } from '@ant-design/icons';
import { useConditions, useSaveCondition, useDeleteCondition } from '../hooks/useFavor';
import type { FavorCondition } from '../api/favor';

const { Title } = Typography;

export const FavorConditionsPage: React.FC = () => {
  const { data, isLoading } = useConditions();
  const saveMutation = useSaveCondition();
  const deleteMutation = useDeleteCondition();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCondition, setEditingCondition] = useState<FavorCondition | null>(null);
  const [form] = Form.useForm();

  const handleAdd = () => {
    setEditingCondition(null);
    form.resetFields();
    setIsModalOpen(true);
  };

  const handleEdit = (record: FavorCondition) => {
    setEditingCondition(record);
    form.setFieldsValue(record);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('已删除');
    } catch {
      message.error('删除失败');
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      await saveMutation.mutateAsync({ ...editingCondition, ...values });
      message.success('保存成功');
      setIsModalOpen(false);
    } catch {
      message.error('保存失败');
    }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '查询语句', dataIndex: 'query', key: 'query', ellipsis: true },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '启用',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => <Switch checked={enabled} disabled />,
    },
    { title: '优先级', dataIndex: 'priority', key: 'priority' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: FavorCondition) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除?"
            onConfirm={() => record.id !== undefined && handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />} loading={deleteMutation.isPending}>
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
              <SettingOutlined /> 选股条件管理
            </Title>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
              新增条件
            </Button>
          </Space>
        </Card>
        <Card>
          <Table
            dataSource={data?.conditions || []}
            columns={columns}
            rowKey="id"
            loading={isLoading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      </Space>

      <Modal
        title={editingCondition ? '编辑条件' : '新增条件'}
        open={isModalOpen}
        onOk={handleSave}
        onCancel={() => setIsModalOpen(false)}
        confirmLoading={saveMutation.isPending}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="条件名称" />
          </Form.Item>
          <Form.Item
            name="query"
            label="查询语句"
            rules={[{ required: true, message: '请输入查询语句' }]}
          >
            <Input.TextArea rows={3} placeholder="选股查询语句" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="条件描述" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="priority" label="优先级">
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="max_results" label="最大结果数">
            <InputNumber min={1} max={1000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="filter_hot_sector" label="板块过滤" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="filter_min_cap_yi" label="最小流通市值(亿)">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
