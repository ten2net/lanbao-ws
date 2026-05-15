import React, { useState } from 'react';
import { Card, Table, Button, Typography, Space, Tag } from 'antd';
import { HistoryOutlined, EyeOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useResearchReports, useResearchReport } from '../hooks/useResearch';
import { StockAnalysisCard } from '../components/AIResearch/StockAnalysisCard';

const { Title } = Typography;

export const AIResearchHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const reportId = searchParams.get('reportId');
  const { data, isLoading } = useResearchReports({ limit: pageSize, offset: (page - 1) * pageSize });
  const { data: reportData, isLoading: reportLoading } = useResearchReport(reportId);

  const columns = [
    { title: '报告ID', dataIndex: 'report_id', key: 'report_id' },
    { title: '生成日期', dataIndex: 'created_at', key: 'created_at' },
    { title: '操作', key: 'action',
      render: (_: any, record: any) => (
        <Button size="small" icon={<EyeOutlined />}
          onClick={() => navigate(`/ai-research/history?reportId=${record.report_id}`)}>查看</Button>
      ),
    },
  ];

  // 显示报告详情
  if (reportId) {
    return (
      <div style={{ padding: 24 }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card>
            <Space style={{ justifyContent: 'space-between', width: '100%' }}>
              <Title level={4} style={{ margin: 0 }}><HistoryOutlined /> 报告详情</Title>
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/ai-research/history')}>返回列表</Button>
            </Space>
          </Card>

          {reportLoading && <Card loading>加载中...</Card>}

          {reportData && (
            <>
              <Card title="市场综述">
                <Space direction="vertical">
                  <p>报告ID: <code>{reportData.report_id}</code></p>
                  <p>报告类型: <Tag>{reportData.report_type}</Tag></p>
                  <p>生成时间: {reportData.created_at}</p>
                  <p>综合评级: <Tag color={reportData.summary.overall_verdict === 'BUY' ? 'green' : reportData.summary.overall_verdict === 'SELL' ? 'red' : 'default'}>{reportData.summary.overall_verdict}</Tag></p>
                  <p>置信度: {(reportData.summary.confidence * 100).toFixed(0)}%</p>
                  <p>市场趋势: {reportData.summary.market_trend}</p>
                </Space>
              </Card>

              {reportData.macro_analysis && (
                <Card title="宏观分析">
                  <Space direction="vertical">
                    <p>市场趋势: {reportData.macro_analysis.market_trend}</p>
                    <p>趋势强度: {(reportData.macro_analysis.trend_strength * 100).toFixed(0)}%</p>
                    <p>热门板块: {reportData.macro_analysis.sector_hot?.join(', ') || '—'}</p>
                    <p>政策影响: {reportData.macro_analysis.policy_impact}</p>
                    <p>风险等级: {reportData.macro_analysis.risk_level}</p>
                  </Space>
                </Card>
              )}

              {reportData.stock_analyses?.map((stock: any) => (
                <StockAnalysisCard
                  key={stock.symbol}
                  symbol={stock.symbol}
                  name={stock.name}
                  synthesis={stock.synthesis}
                  fundamental={stock.fundamental}
                  technical={stock.technical}
                  sentiment={stock.sentiment}
                />
              ))}

              {reportData.portfolio_suggestions && (
                <Card title="投资组合建议">
                  <Space direction="vertical">
                    <p>重点推荐: {reportData.portfolio_suggestions.top_picks?.join(', ') || '—'}</p>
                    <p>建议回避: {reportData.portfolio_suggestions.avoid_list?.join(', ') || '—'}</p>
                  </Space>
                </Card>
              )}
            </>
          )}
        </Space>
      </div>
    );
  }

  // 显示报告列表
  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Title level={4}><HistoryOutlined /> 报告历史</Title>
        <Table dataSource={data?.reports || []} columns={columns} rowKey="report_id" loading={isLoading}
          pagination={{ current: page, pageSize, total: data?.total || 0, onChange: setPage }} />
      </Card>
    </div>
  );
};
