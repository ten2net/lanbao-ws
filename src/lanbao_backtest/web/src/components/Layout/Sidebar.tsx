import { useState } from 'react';
import { Collapse, Select, DatePicker, Tag, Button, Space } from 'antd';
import { useBacktestStore } from '../../stores/backtestStore';
import { useQuery } from '@tanstack/react-query';
import { strategyApi } from '../../api/strategy';

const { Panel } = Collapse;
const { Option } = Select;

export function Sidebar() {
  const { filters, setFilters } = useBacktestStore();
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const { data: strategies } = useQuery({ queryKey: ['strategies'], queryFn: strategyApi.list });
  const allTags = ['优化', '验证', '对比', '2025Q1'];

  return (
    <div style={{ padding: 16 }}>
      <Collapse defaultActiveKey={['1', '2', '3']} ghost>
        <Panel header="策略类型" key="1">
          <Select placeholder="选择策略" allowClear style={{ width: '100%' }}
            value={filters.strategy} onChange={(v) => setFilters({ strategy: v })}
          >
            {strategies?.map((s) => <Option key={s.strategy_id} value={s.strategy_id}>{s.name}</Option>)}
          </Select>
        </Panel>
        <Panel header="标签" key="2">
          <Space wrap>
            {allTags.map((tag) => (
              <Tag key={tag} color={selectedTags.includes(tag) ? 'blue' : undefined}
                style={{ cursor: 'pointer' }}
                onClick={() => {
                  const newTags = selectedTags.includes(tag)
                    ? selectedTags.filter((t) => t !== tag) : [...selectedTags, tag];
                  setSelectedTags(newTags);
                  setFilters({ tags: newTags });
                }}
              >{tag}</Tag>
            ))}
          </Space>
        </Panel>
        <Panel header="日期范围" key="3">
          <DatePicker.RangePicker style={{ width: '100%' }}
            onChange={(dates) => {
              if (dates) {
                setFilters({
                  dateRange: [
                    dates[0]?.format('YYYY-MM-DD') || '',
                    dates[1]?.format('YYYY-MM-DD') || '',
                  ],
                });
              }
            }}
          />
        </Panel>
      </Collapse>
      <Button block style={{ marginTop: 16 }}
        onClick={() => {
          setSelectedTags([]);
          setFilters({ strategy: undefined, symbol: undefined, tags: [], dateRange: undefined });
        }}
      >清除筛选</Button>
    </div>
  );
}
