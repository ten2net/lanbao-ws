import { Button } from 'antd';
import { MoonOutlined, SunOutlined, DesktopOutlined } from '@ant-design/icons';
import { useThemeStore } from '../../stores/themeStore';

export function ThemeToggle() {
  const { mode, toggle } = useThemeStore();

  const iconMap = {
    dark: <MoonOutlined />,
    light: <SunOutlined />,
    auto: <DesktopOutlined />,
  };

  const titleMap = {
    dark: '当前主题: 深色',
    light: '当前主题: 浅色',
    auto: '当前主题: 跟随系统',
  };

  return (
    <Button
      type="text"
      icon={iconMap[mode]}
      onClick={toggle}
      title={titleMap[mode]}
    />
  );
}
