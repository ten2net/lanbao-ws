import { Tag } from 'antd';

const LEVEL_MAP: Record<string, { color: string; label: string }> = {
  CRITICAL: { color: 'red', label: '严重' },
  HIGH: { color: 'orange', label: '高' },
  MEDIUM: { color: 'gold', label: '中' },
  LOW: { color: 'blue', label: '低' },
};

interface AlertBadgeProps {
  level: string;
}

export function AlertBadge({ level }: AlertBadgeProps) {
  const info = LEVEL_MAP[level] || { color: 'default', label: level };
  return <Tag color={info.color}>{info.label}</Tag>;
}
