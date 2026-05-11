import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface StatusPieChartItem {
  name: string;
  value: number;
}

interface StatusPieChartProps {
  data: StatusPieChartItem[];
  title: string;
}

const COLORS = ['#52c41a', '#f5222d', '#faad14', '#8c8c8c'];

export function StatusPieChart({ data, title }: StatusPieChartProps) {
  return (
    <div style={{ height: 280 }}>
      <h4 style={{ marginBottom: 12 }}>{title}</h4>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((_entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
