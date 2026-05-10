import { Outlet } from 'react-router-dom';
import { Layout as AntLayout } from 'antd';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

const { Content, Sider } = AntLayout;

export function Layout() {
  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Header />
      <AntLayout>
        <Sider width={240} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
          <Sidebar />
        </Sider>
        <Content style={{ padding: 24, background: '#fff' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
