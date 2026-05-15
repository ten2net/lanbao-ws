"""AI 投研分析 ROS2 节点"""
import asyncio
import threading
from datetime import datetime

import rclpy
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup

from loguru import logger

from lanbao_core.base_node import LanBaoBaseNode
from lanbao_core.config import NodeConfig
from lanbao_interfaces.action import RunResearch
from lanbao_interfaces.msg import ResearchReport as ResearchReportMsg
from lanbao_interfaces.srv import GetResearchReport

from .orchestrator import AgentOrchestrator
from .llm.client import LLMClient
from .llm.providers.base import LLMConfig
from .data_client.ros2_data_client import ROS2DataClient
from .report_store import ReportStore


class AIResearchNode(LanBaoBaseNode):
    """AI 投研分析节点"""

    def __init__(self):
        config = NodeConfig(
            node_name='ai_research_node',
            node_type='ai_research',
            publish_rate=0.1
        )
        super().__init__('ai_research_node', config)

        self._orchestrator = None
        self._data_client = None
        self._report_store = None
        self._action_server = None
        self._get_report_service = None
        self._report_publisher = None

    def initialize(self) -> bool:
        try:
            self._data_client = ROS2DataClient(self)

            import os
            llm_config = LLMConfig(
                provider="deepseek",
                model="deepseek-chat",
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                temperature=0.3,
            )
            llm_client = LLMClient(llm_config)

            self._orchestrator = AgentOrchestrator(llm_client, self._data_client)
            self._report_store = ReportStore()

            self._setup_action_server()
            self._setup_services()

            self._report_publisher = self.create_publisher(
                ResearchReportMsg,
                '/research/reports',
                self._qos_profiles['default']
            )

            logger.info("AI Research Node 初始化完成")
            return True
        except Exception as e:
            logger.exception(f"AI Research Node 初始化失败: {e}")
            return False

    def _setup_action_server(self):
        self._action_server = ActionServer(
            self,
            RunResearch,
            '/research/run',
            self._handle_run_research,
            callback_group=ReentrantCallbackGroup()
        )
        logger.info("RunResearch Action Server 已启动")

    def _setup_services(self):
        self._get_report_service = self.create_service(
            GetResearchReport,
            '/research/get_report',
            self._handle_get_report
        )

    def _handle_run_research(self, goal_handle):
        """处理研报分析请求 — 后台异步执行，不阻塞 ROS2 executor"""
        request = goal_handle.request
        report_id = request.report_id or f"rpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        research_type = request.research_type
        symbols = list(request.symbols)

        logger.info(f"收到分析请求: {report_id}, type={research_type}, symbols={symbols}")

        def _run_analysis():
            """在后台线程中运行分析，不占用 executor"""
            async def _async_analysis():
                if research_type == "market_daily":
                    report = await self._orchestrator.run_market_daily_research(
                        symbols=symbols, report_id=report_id
                    )
                else:
                    symbol = symbols[0] if symbols else "UNKNOWN"
                    report = await self._orchestrator.run_stock_research(
                        symbol=symbol, report_id=report_id
                    )
                filepath = self._report_store.save(report, self._data_client)
                self._publish_report_notification(report)
                logger.info(f"分析完成并保存: {report_id}, 路径: {filepath}")

            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_async_analysis())
            except Exception as e:
                logger.exception(f"分析执行失败: {e}")
            finally:
                loop.close()

        # 启动后台守护线程执行分析，不等待其完成
        threading.Thread(target=_run_analysis, daemon=True).start()

        # 立即返回，确保 ROS2 executor 不被阻塞，可继续处理 service response
        goal_handle.succeed()
        result = RunResearch.Result()
        result.success = True
        result.report_id = report_id
        result.report_path = ""
        result.error_message = ""
        return result

    def _handle_get_report(self, request, response):
        """直接查询本地 report store 的 JSON 文件"""
        try:
            report_json = self._report_store.load_json(request.report_id)
            if report_json:
                response.found = True
                response.report_json = report_json
                response.created_at = ""
                logger.info(f"报告已找到: {request.report_id}")
            else:
                response.found = False
                response.report_json = ""
                response.created_at = ""
                logger.warning(f"报告不存在: {request.report_id}")
        except Exception as e:
            logger.error(f"获取报告失败: {e}")
            response.found = False
            response.report_json = ""
            response.created_at = ""
        return response

    def _publish_report_notification(self, report):
        msg = ResearchReportMsg()
        msg.report_id = report.report_id
        msg.report_type = report.report_type
        msg.symbols = [s.symbol for s in report.stock_analyses]
        msg.summary = report.summary.market_trend
        msg.verdict = report.summary.overall_verdict
        msg.confidence = report.summary.confidence
        msg.created_at = report.created_at

        self._report_publisher.publish(msg)
        logger.info(f"报告通知已发布: {report.report_id}")

    def start(self) -> bool:
        logger.info("AI Research Node 启动")
        return True

    def stop(self):
        logger.info("AI Research Node 停止")
        if self._action_server:
            self._action_server.destroy()


def main(args=None):
    rclpy.init(args=args)
    node = AIResearchNode()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
