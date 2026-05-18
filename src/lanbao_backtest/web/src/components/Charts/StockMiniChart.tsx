import { useEffect, useRef, useCallback } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  LineData,
  Time,
} from 'lightweight-charts';

export interface KLineItem {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface MacdItem {
  time: string;
  dif: number;
  dea: number;
  macd: number;
}

/** 计算 EMA */
function calcEMA(values: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const ema: number[] = [];
  let prevEma = values[0];
  for (let i = 0; i < values.length; i++) {
    if (i === 0) {
      ema.push(values[0]);
    } else {
      prevEma = values[i] * k + prevEma * (1 - k);
      ema.push(prevEma);
    }
  }
  return ema;
}

/** 计算 MACD */
function calcMACD(data: KLineItem[]): MacdItem[] {
  const closes = data.map((d) => d.close);
  const ema12 = calcEMA(closes, 12);
  const ema26 = calcEMA(closes, 26);
  const dif = ema12.map((v, i) => v - ema26[i]);
  const dea = calcEMA(dif, 9);
  const macd = dif.map((v, i) => (v - dea[i]) * 2);

  return data.map((d, i) => ({
    time: d.time,
    dif: Math.round(dif[i] * 1000) / 1000,
    dea: Math.round(dea[i] * 1000) / 1000,
    macd: Math.round(macd[i] * 1000) / 1000,
  }));
}

interface Props {
  data: KLineItem[];
  width?: number;
}

/** 迷你股票图表：K线 + 成交量 + MACD */
export function StockMiniChart({ data, width = 360 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartsRef = useRef<IChartApi[]>([]);
  const seriesRef = useRef<{
    candle?: ISeriesApi<'Candlestick'>;
    volume?: ISeriesApi<'Histogram'>;
    dif?: ISeriesApi<'Line'>;
    dea?: ISeriesApi<'Line'>;
    macd?: ISeriesApi<'Histogram'>;
  }>({});

  const syncCrosshair = useCallback((sourceChart: IChartApi, charts: IChartApi[]) => {
    const handleCrosshair = (param: any) => {
      const time = param.time;
      charts.forEach((chart) => {
        if (chart !== sourceChart && time) {
          chart.setCrosshairPosition(0, time as Time, {} as any);
        }
      });
    };
    sourceChart.subscribeCrosshairMove(handleCrosshair);
    return () => sourceChart.unsubscribeCrosshairMove(handleCrosshair);
  }, []);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    // 清除旧 chart
    chartsRef.current.forEach((c) => c.remove());
    chartsRef.current = [];

    const macdData = calcMACD(data);

    // 公共 chart 配置
    const commonOptions = {
      width,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#666',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: '#f5f5f5', style: 2 as const },
        horzLines: { color: '#f5f5f5', style: 2 as const },
      },
      crosshair: {
        mode: 1 as const,
        vertLine: { color: '#999', width: 1 as const, style: 2 as const, labelBackgroundColor: '#999' },
        horzLine: { color: '#999', width: 1 as const, style: 2 as const, labelBackgroundColor: '#999' },
      },
      rightPriceScale: {
        borderColor: '#e8e8e8',
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: '#e8e8e8',
        timeVisible: false,
        ticksVisible: false,
      },
      handleScroll: { vertTouchDrag: false },
      handleScale: { axisPressedMouseMove: false },
    };

    // ===== Chart 1: K线 =====
    const chart1 = createChart(containerRef.current, {
      ...commonOptions,
      height: 130,
    });
    const candleSeries = chart1.addCandlestickSeries({
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
    candleSeries.setData(candleData);
    chart1.timeScale().fitContent();

    // ===== Chart 2: 成交量 =====
    const chart2 = createChart(containerRef.current, {
      ...commonOptions,
      height: 70,
    });
    const volumeSeries = chart2.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.2, bottom: 0 },
    });
    const volumeData: HistogramData<Time>[] = data.map((d) => ({
      time: d.time as Time,
      value: d.volume,
      color: d.close >= d.open ? '#f5a3a3' : '#a3d5a3',
    }));
    volumeSeries.setData(volumeData);
    chart2.timeScale().fitContent();

    // ===== Chart 3: MACD =====
    const chart3 = createChart(containerRef.current, {
      ...commonOptions,
      height: 70,
      timeScale: { ...commonOptions.timeScale, visible: true },
    });
    const difSeries = chart3.addLineSeries({
      color: '#f5a623',
      lineWidth: 1,
      priceScaleId: '',
    });
    const deaSeries = chart3.addLineSeries({
      color: '#4a90d9',
      lineWidth: 1,
      priceScaleId: '',
    });
    const macdSeries = chart3.addHistogramSeries({
      priceFormat: { type: 'price', precision: 3, minMove: 0.001 },
      priceScaleId: '',
    });
    // 所有 MACD 系列共享同一个价格刻度
    difSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.1, bottom: 0.1 },
    });

    const difData: LineData<Time>[] = macdData.map((d) => ({
      time: d.time as Time,
      value: d.dif,
    }));
    const deaData: LineData<Time>[] = macdData.map((d) => ({
      time: d.time as Time,
      value: d.dea,
    }));
    const macdHistData: HistogramData<Time>[] = macdData.map((d) => ({
      time: d.time as Time,
      value: d.macd,
      color: d.macd >= 0 ? '#cf304a' : '#228b22',
    }));

    difSeries.setData(difData);
    deaSeries.setData(deaData);
    macdSeries.setData(macdHistData);
    chart3.timeScale().fitContent();

    chartsRef.current = [chart1, chart2, chart3];
    seriesRef.current = { candle: candleSeries, volume: volumeSeries, dif: difSeries, dea: deaSeries, macd: macdSeries };

    // 同步十字准星
    const unsub1 = syncCrosshair(chart1, [chart2, chart3]);
    const unsub2 = syncCrosshair(chart2, [chart1, chart3]);
    const unsub3 = syncCrosshair(chart3, [chart1, chart2]);

    // 同步时间轴滚动/缩放
    const syncTimeScale = (source: IChartApi, targets: IChartApi[]) => {
      const handler = () => {
        const logicalRange = source.timeScale().getVisibleLogicalRange();
        if (logicalRange) {
          targets.forEach((t) => t.timeScale().setVisibleLogicalRange(logicalRange));
        }
      };
      source.timeScale().subscribeVisibleLogicalRangeChange(handler);
      return () => source.timeScale().unsubscribeVisibleLogicalRangeChange(handler);
    };
    const unsubTs1 = syncTimeScale(chart1, [chart2, chart3]);
    const unsubTs2 = syncTimeScale(chart2, [chart1, chart3]);
    const unsubTs3 = syncTimeScale(chart3, [chart1, chart2]);

    return () => {
      unsub1();
      unsub2();
      unsub3();
      unsubTs1();
      unsubTs2();
      unsubTs3();
      chartsRef.current.forEach((c) => c.remove());
      chartsRef.current = [];
    };
  }, [data, width, syncCrosshair]);

  if (!data || data.length === 0) {
    return <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无K线数据</div>;
  }

  return <div ref={containerRef} style={{ width }} />;
}
