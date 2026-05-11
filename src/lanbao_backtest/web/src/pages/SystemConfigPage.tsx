import { useEffect } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Switch,
  Select,
  TimePicker,
  Button,
  Card,
  Skeleton,
  Anchor,
  message,
  Modal,
} from 'antd';
import dayjs from 'dayjs';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { configApi } from '../api/config';
import { useConfigStore } from '../stores/configStore';
import type { SystemConfig } from '../types/config';

const { Option } = Select;

const ANCHOR_ITEMS = [
  { key: 'backtest', href: '#backtest', title: '回测参数' },
  { key: 'risk', href: '#risk', title: '风险控制' },
  { key: 'data_sync', href: '#data_sync', title: '数据同步' },
  { key: 'notification', href: '#notification', title: '通知设置' },
];

const SOURCE_OPTIONS = [
  { value: 'tushare,akshare', label: 'Tushare > AKShare' },
  { value: 'akshare,tushare', label: 'AKShare > Tushare' },
];

const ALERT_LEVEL_OPTIONS = [
  { value: 'info', label: '信息' },
  { value: 'warning', label: '警告' },
  { value: 'critical', label: '严重' },
];

const DEFAULT_CONFIG: SystemConfig = {
  backtest: {
    default_initial_capital: 100000,
    default_commission_rate: 0.0003,
    default_slippage: 0.001,
    default_backtest_days: 365,
  },
  risk: {
    max_single_loss_pct: 0.02,
    max_drawdown_threshold: 0.15,
    max_position_pct: 0.8,
    circuit_breaker_enabled: true,
  },
  data_sync: {
    auto_sync_enabled: true,
    sync_time: '09:00',
    source_priority: 'tushare,akshare',
  },
  notification: {
    webhook_url: null,
    alert_level_threshold: 'warning',
  },
};

function pctFormatter(v: number | string | undefined): string {
  if (v == null) return '0%';
  return `${(Number(v) * 100).toFixed(0)}%`;
}

function pctParser(v: string | undefined): number {
  return Number((v || '0').replace('%', '')) / 100;
}

function moneyFormatter(v: number | string | undefined): string {
  if (v == null) return '¥ 0';
  const num = Number(v);
  return `¥ ${num.toFixed(0)}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function moneyParser(v: string | undefined): number {
  if (!v) return 0;
  return Number(v.replace(/[¥,\s]/g, ''));
}

export function SystemConfigPage() {
  const [form] = Form.useForm<SystemConfig>();
  const qc = useQueryClient();
  const { setConfig, setLoading, setSaving } = useConfigStore();

  const { data: configData, isLoading } = useQuery({
    queryKey: ['config'],
    queryFn: configApi.get,
  });

  useEffect(() => {
    setLoading(isLoading);
  }, [isLoading, setLoading]);

  useEffect(() => {
    if (configData) {
      setConfig(configData);
      // Convert sync_time string to dayjs for TimePicker
      const formValues = {
        ...configData,
        data_sync: {
          ...configData.data_sync,
          sync_time: dayjs(configData.data_sync.sync_time, 'HH:mm'),
        },
      };
      form.setFieldsValue(formValues as any);
    }
  }, [configData, form, setConfig]);

  const updateMutation = useMutation({
    mutationFn: configApi.update,
    onMutate: () => {
      setSaving(true);
    },
    onSettled: () => {
      setSaving(false);
    },
    onSuccess: (data) => {
      message.success('配置保存成功');
      setConfig(data);
      qc.invalidateQueries({ queryKey: ['config'] });
    },
    onError: (err: Error) => {
      message.error(`保存失败: ${err.message}`);
    },
  });

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      // Convert dayjs back to string for sync_time
      const payload: SystemConfig = {
        ...values,
        data_sync: {
          ...values.data_sync,
          sync_time: (values.data_sync.sync_time as unknown as dayjs.Dayjs).format('HH:mm'),
        },
      };
      updateMutation.mutate(payload);
    } catch {
      // validation failed, do nothing
    }
  };

  const handleReset = () => {
    Modal.confirm({
      title: '确认重置为默认值？',
      content: '此操作将覆盖当前所有配置，且不可撤销。',
      okText: '确认重置',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        const formValues = {
          ...DEFAULT_CONFIG,
          data_sync: {
            ...DEFAULT_CONFIG.data_sync,
            sync_time: dayjs(DEFAULT_CONFIG.data_sync.sync_time, 'HH:mm'),
          },
        };
        form.setFieldsValue(formValues as any);
        message.info('已重置为默认值，请保存以生效');
      },
    });
  };

  if (isLoading) {
    return (
      <div style={{ padding: 24 }}>
        <Skeleton active paragraph={{ rows: 12 }} />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', padding: 24, gap: 24 }}>
      {/* Left Anchor Navigation */}
      <div style={{ width: 160, flexShrink: 0 }}>
        <Anchor
          items={ANCHOR_ITEMS.map((item) => ({
            key: item.key,
            href: item.href,
            title: item.title,
          }))}
        />
      </div>

      {/* Right Form Area */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <Form form={form} layout="vertical">
          {/* Backtest Config */}
          <Card id="backtest" title="回测参数" style={{ marginBottom: 24 }}>
            <Form.Item
              name={['backtest', 'default_initial_capital']}
              label="默认初始资金"
              rules={[{ required: true, message: '请输入初始资金' }, { type: 'number', min: 0.01, message: '必须大于0' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0.01}
                step={1000}
                formatter={moneyFormatter}
                parser={moneyParser}
              />
            </Form.Item>
            <Form.Item
              name={['backtest', 'default_commission_rate']}
              label="默认佣金率"
              rules={[{ required: true, message: '请输入佣金率' }, { type: 'number', min: 0, max: 0.01, message: '必须在0-1%之间' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={0.01}
                step={0.0001}
                formatter={pctFormatter}
                parser={pctParser}
              />
            </Form.Item>
            <Form.Item
              name={['backtest', 'default_slippage']}
              label="默认滑点"
              rules={[{ required: true, message: '请输入滑点' }, { type: 'number', min: 0, max: 0.05, message: '必须在0-5%之间' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={0.05}
                step={0.0001}
                formatter={pctFormatter}
                parser={pctParser}
              />
            </Form.Item>
            <Form.Item
              name={['backtest', 'default_backtest_days']}
              label="默认回测天数"
              rules={[{ required: true, message: '请输入回测天数' }, { type: 'number', min: 1, message: '必须大于0' }]}
            >
              <InputNumber style={{ width: '100%' }} min={1} step={1} />
            </Form.Item>
          </Card>

          {/* Risk Config */}
          <Card id="risk" title="风险控制" style={{ marginBottom: 24 }}>
            <Form.Item
              name={['risk', 'max_single_loss_pct']}
              label="最大单笔亏损比例"
              rules={[{ required: true, message: '请输入最大单笔亏损比例' }, { type: 'number', min: 0, max: 1, message: '必须在0-100%之间' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={1}
                step={0.01}
                formatter={pctFormatter}
                parser={pctParser}
              />
            </Form.Item>
            <Form.Item
              name={['risk', 'max_drawdown_threshold']}
              label="最大回撤阈值"
              rules={[{ required: true, message: '请输入最大回撤阈值' }, { type: 'number', min: 0, max: 1, message: '必须在0-100%之间' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={1}
                step={0.01}
                formatter={pctFormatter}
                parser={pctParser}
              />
            </Form.Item>
            <Form.Item
              name={['risk', 'max_position_pct']}
              label="仓位上限"
              rules={[{ required: true, message: '请输入仓位上限' }, { type: 'number', min: 0, max: 1, message: '必须在0-100%之间' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={1}
                step={0.01}
                formatter={pctFormatter}
                parser={pctParser}
              />
            </Form.Item>
            <Form.Item
              name={['risk', 'circuit_breaker_enabled']}
              label="熔断开关"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Card>

          {/* Data Sync Config */}
          <Card id="data_sync" title="数据同步" style={{ marginBottom: 24 }}>
            <Form.Item
              name={['data_sync', 'auto_sync_enabled']}
              label="自动同步开关"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
            <Form.Item
              name={['data_sync', 'sync_time']}
              label="同步时间"
              rules={[{ required: true, message: '请选择同步时间' }]}
            >
              <TimePicker format="HH:mm" style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name={['data_sync', 'source_priority']}
              label="数据源优先级"
              rules={[{ required: true, message: '请选择数据源优先级' }]}
            >
              <Select>
                {SOURCE_OPTIONS.map((opt) => (
                  <Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Card>

          {/* Notification Config */}
          <Card id="notification" title="通知设置" style={{ marginBottom: 24 }}>
            <Form.Item
              name={['notification', 'webhook_url']}
              label="Webhook URL"
              rules={[
                {
                  validator: (_: any, value: string | null) => {
                    if (!value) return Promise.resolve();
                    try {
                      new URL(value);
                      return Promise.resolve();
                    } catch {
                      return Promise.reject(new Error('请输入有效的 URL'));
                    }
                  },
                },
              ]}
            >
              <Input placeholder="https://hooks.example.com/..." allowClear />
            </Form.Item>
            <Form.Item
              name={['notification', 'alert_level_threshold']}
              label="告警级别阈值"
              rules={[{ required: true, message: '请选择告警级别阈值' }]}
            >
              <Select>
                {ALERT_LEVEL_OPTIONS.map((opt) => (
                  <Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Card>
        </Form>

        {/* Fixed Bottom Action Bar */}
        <div
          style={{
            position: 'sticky',
            bottom: 0,
            background: '#fff',
            padding: '16px 0',
            borderTop: '1px solid #f0f0f0',
            display: 'flex',
            gap: 12,
            justifyContent: 'flex-end',
          }}
        >
          <Button onClick={handleReset}>重置为默认值</Button>
          <Button type="primary" onClick={handleSave} loading={updateMutation.isPending}>
            保存配置
          </Button>
        </div>
      </div>
    </div>
  );
}
