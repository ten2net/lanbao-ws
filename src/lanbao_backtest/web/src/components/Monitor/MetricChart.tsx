import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useThemeStore } from '../../stores/themeStore';

interface MetricChartDataPoint {
  time: string;
  value: number;
}

interface MetricChartProps {
  data: MetricChartDataPoint[];
  title: string;
  color?: string;
  unit?: string;
}

export function MetricChart({ data, title, color = '#1677ff', unit = '' }: MetricChartProps) {
  const isDark = useThemeStore((state) => state.isDark);

  const axisColor = isDark ? '#a6a6a6' : '#666';
  const gridColor = isDark ? '#333' : '#eee';

  return (
    <div className="metric-chart-container" style={{ height: 280 }}>
      <h4 style={{ marginBottom: 12 }}>{title}</h4>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="time" tick={{ fill: axisColor, fontSize: 12 }} stroke={axisColor} />
          <YAxis
            tick={{ fill: axisColor, fontSize: 12 }}
            stroke={axisColor}
            unit={unit}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: isDark ? '#1f1f1f' : '#fff',
              borderColor: isDark ? '#333' : '#ddd',
              color: isDark ? '#fff' : '#333',
            }}
            formatter={(value: number) => [`${value}${unit}`, title]}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
