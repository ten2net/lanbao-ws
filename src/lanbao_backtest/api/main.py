"""FastAPI 应用主入口 — 回测面板后端网关"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .ros2_client import get_ros2_manager
from .routes import backtests, strategies, data, config
from .services.storage import storage
from .websocket import progress_bridge


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理"""
    # 启动时
    logger.info("FastAPI 启动，初始化 ROS2 连接...")
    manager = get_ros2_manager()
    manager.connect()

    # 注册 Topic 订阅器（回测结果自动持久化）
    _setup_topic_subscriber(manager)

    yield

    # 关闭时
    logger.info("FastAPI 关闭，断开 ROS2 连接...")
    manager.disconnect()


def _setup_topic_subscriber(manager):
    """设置 /backtest/result Topic 订阅器"""
    try:
        from rclpy.qos import QoSProfile
        from lanbao_interfaces.msg import BacktestResult as BacktestResultMsg

        def on_result(msg):
            """接收回测结果并持久化到 JSON"""
            try:
                from datetime import datetime

                # 构造 v2.0 主文件数据
                data = {
                    "schema_version": "2.0",
                    "backtest_id": msg.backtest_id,
                    "meta": {
                        "strategy_id": msg.strategy_id,
                        "strategy_name": msg.strategy_id,
                        "symbol": msg.symbol,
                        "start_date": msg.start_date,
                        "end_date": msg.end_date,
                        "status": msg.status.lower() if msg.status else "completed",
                        "created_at": datetime.now().isoformat(),
                    },
                    "performance": {
                        "returns": {
                            "total_return_pct": round(msg.total_return * 100, 2),
                            "annual_return_pct": round(msg.annual_return * 100, 2),
                        },
                        "risk": {
                            "sharpe_ratio": round(msg.sharpe_ratio, 2),
                            "max_drawdown_pct": round(msg.max_drawdown * 100, 2),
                            "volatility_annual_pct": round(msg.volatility * 100, 2),
                        },
                        "trades": {
                            "total_count": msg.total_trades,
                            "win_rate_pct": round(msg.win_rate * 100, 2),
                            "profit_factor": round(msg.profit_factor, 2),
                        },
                    },
                    "files": {},
                }
                storage.save_backtest(msg.backtest_id, data)
                logger.info(f"Topic 自动持久化回测结果: {msg.backtest_id}")
            except Exception as e:
                logger.error(f"Topic 持久化回测结果失败: {e}")

        manager.node.create_subscription(
            BacktestResultMsg,
            '/backtest/result',
            on_result,
            qos_profile=QoSProfile(depth=10)
        )
        logger.info("已订阅 /backtest/result Topic")

    except Exception as e:
        logger.error(f"注册 Topic 订阅器失败: {e}")


app = FastAPI(
    title="揽宝回测面板 API",
    description="揽宝智能投研交易平台 — 回测管理与分析后端",
    version="0.6.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(backtests.router, prefix="/api/v1", tags=["backtests"])
app.include_router(strategies.router, prefix="/api/v1", tags=["strategies"])
app.include_router(data.router, prefix="/api/v1", tags=["data"])
app.include_router(config.router, prefix="/api/v1", tags=["config"])


@app.get("/health")
async def health_check():
    """健康检查端点"""
    manager = get_ros2_manager()
    return {
        "status": "ok",
        "ros2_connected": manager.is_connected,
    }
