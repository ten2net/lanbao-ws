import React, { useState, useEffect } from 'react';
import { Card, Input, Button, message, Space, Typography } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import { useTriggerStockResearch, useResearchStatus, useResearchReport } from '../hooks/useResearch';
import { ResearchProgress } from '../components/AIResearch/ResearchProgress';
import { StockAnalysisCard } from '../components/AIResearch/StockAnalysisCard';

const { Title } = Typography;

export const AIResearchStockPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [symbol, setSymbol] = useState('');
  const [activeReportId, setActiveReportId] = useState<string | null>(searchParams.get('reportId'));

  const triggerStock = useTriggerStockResearch();
  const { data: statusData } = useResearchStatus(activeReportId);
  const { data: reportData } = useResearchReport(
    statusData?.status === 'completed' ? activeReportId : null
  );

  useEffect(() => {
    const reportId = searchParams.get('reportId');
    if (reportId) setActiveReportId(reportId);
  }, [searchParams]);

  const handleAnalyze = async () => {
    if (!symbol.trim()) { message.warning('请输入股票代码'); return; }
    try {
      const result = await triggerStock.mutateAsync(symbol.trim());
      setActiveReportId(result.report_id);
      setSearchParams({ reportId: result.report_id });
      message.success(`已开始分析: ${symbol}`);
    } catch (e) { message.error('分析失败'); }
  };

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Title level={4}>个股智能研究</Title>
          <Space.Compact style={{ width: '100%', maxWidth: 500 }}>
            <Input placeholder="请输入股票代码 (如: 600519)" value={symbol}
              onChange={(e) => setSymbol(e.target.value)} onPressEnter={handleAnalyze}
              prefix={<SearchOutlined />} />
            <Button type="primary" onClick={handleAnalyze} loading={triggerStock.isPending}>开始分析</Button>
          </Space.Compact>
        </Card>

        {activeReportId && statusData && (
          <ResearchProgress status={statusData.status} progress={statusData.progress}
            message={statusData.message} currentAgent={statusData.current_agent} />
        )}

        {reportData && (
          <Card title="分析报告">
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div>
                <Title level={5}>市场综述</Title>
                <p>综合评级: <strong>{reportData.summary.overall_verdict}</strong></p>
                <p>置信度: {(reportData.summary.confidence * 100).toFixed(0)}%</p>
              </div>
              {reportData.stock_analyses?.map((stock) => (
                <StockAnalysisCard key={stock.symbol} symbol={stock.symbol} name={stock.name}
                  synthesis={stock.synthesis} />
              ))}
            </Space>
          </Card>
        )}
      </Space>
    </div>
  );
};
