import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface EquityPoint {
  date: string;
  equity: number;
  drawdown_pct: number;
  daily_return_pct: number;
}

interface Props {
  data: EquityPoint[];
  showDrawdown?: boolean;
}

function formatDate(ts: string) {
  if (ts.length === 8) {
    return `${ts.slice(0, 4)}-${ts.slice(4, 6)}-${ts.slice(6, 8)}`;
  }
  return ts;
}

export function EquityCurve({ data, showDrawdown = false }: Props) {
  if (!data || data.length === 0) {
    return <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>;
  }

  const chartData = data.map((d) => ({
    ...d,
    dateLabel: formatDate(d.date),
  }));

  return (
    <ResponsiveContainer width="100%" height={showDrawdown ? 360 : 280}>
      <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#1677ff" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#1677ff" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="dateLabel"
          tick={{ fontSize: 11 }}
          tickMargin={8}
          minTickGap={40}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          tickFormatter={(v: number) => `${(v / 10000).toFixed(1)}万`}
          width={60}
        />
        <Tooltip
          formatter={(value: number, name: string) => {
            if (name === 'equity') return [`${value.toFixed(2)}`, '权益'];
            if (name === 'drawdown_pct') return [`${(value * 100).toFixed(2)}%`, '回撤'];
            return [value, name];
          }}
          labelFormatter={(label: string) => label}
        />
        <Area
          type="monotone"
          dataKey="equity"
          stroke="#1677ff"
          strokeWidth={2}
          fill="url(#equityGradient)"
          dot={false}
          activeDot={{ r: 4 }}
        />
        {showDrawdown && (
          <Area
            type="monotone"
            dataKey="drawdown_pct"
            stroke="#cf304a"
            strokeWidth={1}
            fill="none"
            dot={false}
            yAxisId={1}
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}
