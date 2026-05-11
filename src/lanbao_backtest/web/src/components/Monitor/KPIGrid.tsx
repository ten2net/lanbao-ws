import { Row, Col, Card, Statistic } from 'antd';

interface KPIGridItem {
  title: string;
  value: number | string;
  suffix?: string;
  precision?: number;
}

interface KPIGridProps {
  data: KPIGridItem[];
}

export function KPIGrid({ data }: KPIGridProps) {
  return (
    <Row gutter={[16, 16]}>
      {data.map((item, index) => (
        <Col key={index} xs={12} sm={12} md={6}>
          <Card>
            <Statistic
              title={item.title}
              value={item.value}
              suffix={item.suffix}
              precision={item.precision}
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
}
