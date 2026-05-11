import { Menu } from 'antd';
import {
  LineChartOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

interface TopNavProps {
  activeModule: string;
  onModuleChange: (module: string) => void;
}

const moduleItems = [
  { key: 'research', label: '投研中心', icon: <LineChartOutlined />, path: '/' },
  { key: 'monitor', label: '实时监控', icon: <DashboardOutlined />, path: '/system-overview' },
  { key: 'data', label: '数据管理', icon: <DatabaseOutlined />, path: '/data-center' },
  { key: 'settings', label: '系统设置', icon: <SettingOutlined />, path: '/system-config' },
];

export function TopNav({ activeModule, onModuleChange }: TopNavProps) {
  const handleClick: MenuProps['onClick'] = (e) => {
    const moduleKey = e.key;
    onModuleChange(moduleKey);
  };

  return (
    <Menu
      mode="horizontal"
      selectedKeys={[activeModule]}
      onClick={handleClick}
      items={moduleItems.map((item) => ({
        key: item.key,
        label: item.label,
        icon: item.icon,
      }))}
      style={{ flex: 1, minWidth: 0, borderBottom: 'none' }}
    />
  );
}
