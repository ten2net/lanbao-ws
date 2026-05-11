import { useEffect, useState, useCallback } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Layout, theme } from 'antd';
import { TopNav } from './TopNav';
import { SideNav } from './SideNav';
import { ConnectionStatus } from './ConnectionStatus';
import { ThemeToggle } from '../ThemeToggle/ThemeToggle';
import { ros2WS } from '../../services/ros2WebSocket';
import { useThemeStore } from '../../stores/themeStore';

const { Header, Sider, Content } = Layout;

const pathToModuleMap: Record<string, string> = {
  '/': 'research',
  '/backtest': 'research',
  '/compare': 'research',
  '/param-analysis': 'research',
  '/system-overview': 'monitor',
  '/node-status': 'monitor',
  '/risk-monitor': 'monitor',
  '/data-center': 'data',
  '/system-config': 'settings',
};

function getModuleFromPath(path: string): string {
  // Handle nested paths like /backtest/:id
  for (const [prefix, module] of Object.entries(pathToModuleMap)) {
    if (path === prefix || path.startsWith(prefix + '/')) {
      return module;
    }
  }
  return 'research';
}

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const isDark = useThemeStore((state) => state.isDark);
  const [activeModule, setActiveModule] = useState(() =>
    getModuleFromPath(location.pathname),
  );

  const {
    token: { colorBgContainer, colorBgLayout },
  } = theme.useToken();

  useEffect(() => {
    setActiveModule(getModuleFromPath(location.pathname));
  }, [location.pathname]);

  useEffect(() => {
    ros2WS.connect();
    return () => {
      ros2WS.disconnect();
    };
  }, []);

  const handleModuleChange = useCallback(
    (module: string) => {
      setActiveModule(module);
      const pathMap: Record<string, string> = {
        research: '/',
        monitor: '/system-overview',
        data: '/data-center',
        settings: '/system-config',
      };
      navigate(pathMap[module] || '/');
    },
    [navigate],
  );

  return (
    <Layout style={{ minHeight: '100vh', background: colorBgLayout }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          background: colorBgContainer,
          borderBottom: `1px solid ${isDark ? '#303030' : '#f0f0f0'}`,
        }}
      >
        <div
          style={{
            fontSize: 18,
            fontWeight: 600,
            marginRight: 32,
            whiteSpace: 'nowrap',
          }}
        >
          揽宝投研
        </div>
        <TopNav activeModule={activeModule} onModuleChange={handleModuleChange} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginLeft: 'auto' }}>
          <ConnectionStatus />
          <ThemeToggle />
        </div>
      </Header>
      <Layout>
        <Sider
          width={200}
          style={{
            background: colorBgContainer,
            borderRight: `1px solid ${isDark ? '#303030' : '#f0f0f0'}`,
          }}
        >
          <SideNav activeModule={activeModule} />
        </Sider>
        <Content style={{ padding: 24, overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
