import { Menu } from 'antd';
import {
  BarChartOutlined,
  LineChartOutlined,
  SettingOutlined,
  DashboardOutlined,
  ClusterOutlined,
  AlertOutlined,
  DatabaseOutlined,
  ToolOutlined,
  FileTextOutlined,
  SearchOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import type { MenuProps } from 'antd';

interface SideNavProps {
  activeModule: string;
}

const menuConfig: Record<string, MenuProps['items']> = {
  research: [
    { key: '/', label: '回测列表', icon: <BarChartOutlined /> },
    { key: '/compare', label: '批量对比', icon: <LineChartOutlined /> },
    { key: '/param-analysis', label: '参数分析', icon: <SettingOutlined /> },
    { key: '/ai-research/daily', label: 'AI日报', icon: <FileTextOutlined /> },
    { key: '/ai-research/stock', label: '个股研究', icon: <SearchOutlined /> },
    { key: '/ai-research/history', label: '报告历史', icon: <HistoryOutlined /> },
  ],
  monitor: [
    { key: '/system-overview', label: '系统概览', icon: <DashboardOutlined /> },
    { key: '/node-status', label: '节点状态', icon: <ClusterOutlined /> },
    { key: '/risk-monitor', label: '风险监控', icon: <AlertOutlined /> },
  ],
  data: [
    { key: '/data-center', label: '数据底座', icon: <DatabaseOutlined /> },
  ],
  settings: [
    { key: '/system-config', label: '系统配置', icon: <ToolOutlined /> },
  ],
};

export function SideNav({ activeModule }: SideNavProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const items = menuConfig[activeModule] || [];

  const handleClick: MenuProps['onClick'] = (e) => {
    navigate(e.key);
  };

  return (
    <Menu
      mode="inline"
      selectedKeys={[location.pathname]}
      onClick={handleClick}
      items={items}
      style={{ height: '100%', borderRight: 'none' }}
    />
  );
}
