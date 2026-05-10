import { Layout, Menu } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import { LineChartOutlined, BarChartOutlined, SettingOutlined } from '@ant-design/icons';

const { Header: AntHeader } = Layout;

export function Header() {
  const location = useLocation();
  const items = [
    { key: '/', icon: <LineChartOutlined />, label: <Link to="/">回测列表</Link> },
    { key: '/compare', icon: <BarChartOutlined />, label: <Link to="/compare">批量对比</Link> },
    { key: '/param-analysis', icon: <SettingOutlined />, label: <Link to="/param-analysis">参数分析</Link> },
  ];
  return (
    <AntHeader style={{ background: '#fff', borderBottom: '1px solid #f0f0f0', padding: 0 }}>
      <div style={{ float: 'left', padding: '0 24px', fontSize: 18, fontWeight: 'bold' }}>揽宝回测平台</div>
      <Menu mode="horizontal" selectedKeys={[location.pathname]} items={items} style={{ borderBottom: 'none' }} />
    </AntHeader>
  );
}
