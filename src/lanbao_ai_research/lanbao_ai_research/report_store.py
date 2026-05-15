"""报告存储模块"""
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from .models import ResearchReport


class ReportStore:
    """报告存储器"""

    def __init__(self, storage_path: str = "./reports"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, report: ResearchReport, data_client) -> str:
        date_str = datetime.now().strftime("%Y-%m")
        date_dir = self.storage_path / date_str
        date_dir.mkdir(exist_ok=True)

        filename = f"{report.report_id}.md"
        filepath = date_dir / filename

        markdown = self._to_markdown(report)
        filepath.write_text(markdown, encoding='utf-8')

        # 同时保存 JSON，方便 Service 查询
        json_filepath = date_dir / f"{report.report_id}.json"
        json_filepath.write_text(report.to_json(), encoding='utf-8')

        # 保存元数据到 DuckDB（通过 Service）
        try:
            import asyncio
            asyncio.create_task(data_client.save_report_metadata(
                report_id=report.report_id,
                report_type=report.report_type,
                symbols=[s.symbol for s in report.stock_analyses],
                summary=report.summary.market_trend,
                verdict=report.summary.overall_verdict,
                confidence=report.summary.confidence,
                report_json=report.to_json()
            ))
        except Exception as e:
            logger.warning(f"保存报告元数据失败: {e}")

        logger.info(f"报告已保存: {filepath}")
        return str(filepath)

    def load_json(self, report_id: str) -> Optional[str]:
        """加载报告的 JSON 内容，旧报告无 JSON 时回退到 markdown"""
        import json

        for date_dir in self.storage_path.iterdir():
            if date_dir.is_dir():
                json_file = date_dir / f"{report_id}.json"
                if json_file.exists():
                    return json_file.read_text(encoding='utf-8')

                # 回退：旧报告只有 markdown，包装为简化 JSON
                md_file = date_dir / f"{report_id}.md"
                if md_file.exists():
                    markdown = md_file.read_text(encoding='utf-8')
                    return json.dumps({
                        "report_id": report_id,
                        "report_type": "market_daily",
                        "created_at": "",
                        "summary": {
                            "market_trend": markdown,
                            "overall_verdict": "HOLD",
                            "confidence": 0.5,
                            "top_sectors": [],
                            "risk_level": "中"
                        },
                        "stock_analyses": [],
                        "portfolio_suggestions": {}
                    }, ensure_ascii=False)
        return None

    def load(self, report_id: str) -> Optional[str]:
        for date_dir in self.storage_path.iterdir():
            if date_dir.is_dir():
                filepath = date_dir / f"{report_id}.md"
                if filepath.exists():
                    return filepath.read_text(encoding='utf-8')
        return None

    def _to_markdown(self, report: ResearchReport) -> str:
        lines = [
            f"# 揽宝智能投研报告 — {report.report_id}",
            "",
            f"**报告类型**: {report.report_type} | **生成时间**: {report.created_at}",
            "",
            "---",
            "",
            "## 市场综述",
            "",
            f"**综合评级**: {report.summary.overall_verdict} | **置信度**: {report.summary.confidence:.0%}",
            "",
            f"{report.summary.market_trend}",
            "",
        ]

        if report.macro_analysis:
            lines.extend([
                "## 一、宏观环境分析", "",
                f"**市场趋势**: {report.macro_analysis.market_trend} (强度: {report.macro_analysis.trend_strength:.0%})", "",
                f"**热门板块**: {', '.join(report.macro_analysis.sector_hot)}", "",
                f"**政策影响**: {report.macro_analysis.policy_impact}", "",
                f"**风险等级**: {report.macro_analysis.risk_level}", "",
            ])

        if report.stock_analyses:
            lines.extend(["## 二、个股深度分析", ""])
            for stock in report.stock_analyses:
                lines.extend([f"### {stock.symbol} {stock.name}", ""])
                if stock.synthesis:
                    lines.extend([
                        f"**综合评级**: {stock.synthesis.verdict} | **得分**: {stock.synthesis.score}", "",
                        "**看多理由**:",
                    ])
                    for reason in stock.synthesis.bull_case:
                        lines.append(f"- {reason}")
                    lines.append("")
                    lines.append("**看空理由**:")
                    for reason in stock.synthesis.bear_case:
                        lines.append(f"- {reason}")
                    lines.append("")
                    if stock.synthesis.position_suggestion:
                        lines.append(f"**仓位建议**: {stock.synthesis.position_suggestion}")
                    if stock.synthesis.risk_notes:
                        lines.append("**风险提示**:")
                        for note in stock.synthesis.risk_notes:
                            lines.append(f"- {note}")
                    lines.append("")

        if report.portfolio_suggestions:
            lines.extend(["## 三、投资组合建议", ""])
            if report.portfolio_suggestions.top_picks:
                lines.append(f"**重点推荐**: {', '.join(report.portfolio_suggestions.top_picks)}")
            if report.portfolio_suggestions.avoid_list:
                lines.append(f"**建议回避**: {', '.join(report.portfolio_suggestions.avoid_list)}")
            lines.append("")

        lines.extend([
            "---", "",
            "*本报告由揽宝智能投研系统生成，仅供参考，不构成投资建议。*",
        ])

        return "\n".join(lines)
