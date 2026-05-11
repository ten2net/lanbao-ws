import { Tag } from 'antd';

const LEVEL_MAP: Record<string, { color: string; label: string }> = {
  CRITICAL: { color: 'red', label: '严重' },
  ERROR: { color: 'orange', label: '错误' },
  WARNING: { color: 'gold', label: '警告' },
  INFO: { color: 'blue', label: '信息' },
};

interface AlertBadgeProps {
  level: string;
}

export function AlertBadge({ level }: AlertBadgeProps) {
  const info = LEVEL_MAP[level] || { color: 'default', label: level };
  return <Tag color={info.color}>{info.label}</Tag>;
}
