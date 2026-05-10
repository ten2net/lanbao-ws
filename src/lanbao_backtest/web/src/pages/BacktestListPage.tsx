import { Typography, Button, Modal, Form, Input, DatePicker, Select, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { BacktestTable } from '../components/BacktestTable/BacktestTable';
import { useRunBacktest } from '../hooks/useBacktests';

const { Title } = Typography;
const { Option } = Select;

export function BacktestListPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();
  const runMutation = useRunBacktest();

  const handleRun = async (values: any) => {
    try {
      await runMutation.mutateAsync({
        strategy_id: values.strategy_id,
        symbol: values.symbol,
        start_date: values.dateRange[0].format('YYYYMMDD'),
        end_date: values.dateRange[1].format('YYYYMMDD'),
        params: {},
      });
      message.success('回测已启动');
      setIsModalOpen(false);
      form.resetFields();
    } catch (error) {
      message.error(`启动失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>回测列表</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsModalOpen(true)}>
          运行新回测
        </Button>
      </div>
      <BacktestTable />
      <Modal title="运行新回测" open={isModalOpen} onCancel={() => setIsModalOpen(false)}
        onOk={() => form.submit()} confirmLoading={runMutation.isPending}>
        <Form form={form} onFinish={handleRun} layout="vertical">
          <Form.Item name="strategy_id" label="策略" rules={[{ required: true }]} initialValue="ma_cross">
            <Select>
              <Option value="ma_cross">双均线交叉策略</Option>
              <Option value="rsi">RSI策略</Option>
              <Option value="macd">MACD策略</Option>
            </Select>
          </Form.Item>
          <Form.Item name="symbol" label="股票代码" rules={[{ required: true }]} initialValue="000001.SZ">
            <Input />
          </Form.Item>
          <Form.Item name="dateRange" label="日期范围" rules={[{ required: true }]}>
            <DatePicker.RangePicker />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
