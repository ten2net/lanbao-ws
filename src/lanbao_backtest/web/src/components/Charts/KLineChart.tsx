import { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts';

interface KLineData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface TradeMarker {
  time: string;
  position: 'aboveBar' | 'belowBar';
  color: string;
  shape: 'arrowUp' | 'arrowDown';
  text: string;
}

interface Props {
  data: KLineData[];
  trades?: TradeMarker[];
  height?: number;
}

export function KLineChart({ data, trades, height = 400 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: '#e0e0e0' },
      timeScale: { borderColor: '#e0e0e0', timeVisible: false },
    });

    const series = chart.addCandlestickSeries({
      upColor: '#cf304a',
      downColor: '#228b22',
      borderUpColor: '#cf304a',
      borderDownColor: '#228b22',
      wickUpColor: '#cf304a',
      wickDownColor: '#228b22',
    });

    const candleData: CandlestickData<Time>[] = data.map((d) => ({
      time: d.time as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    series.setData(candleData);

    if (trades && trades.length > 0) {
      series.setMarkers(
        trades.map((t) => ({
          time: t.time as Time,
          position: t.position,
          color: t.color,
          shape: t.shape,
          text: t.text,
          size: 2,
        }))
      );
    }

    chart.timeScale().fitContent();
    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, trades, height]);

  if (!data || data.length === 0) {
    return <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无K线数据</div>;
  }

  return <div ref={containerRef} style={{ width: '100%' }} />;
}
