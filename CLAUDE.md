# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

揽宝智能投研交易平台 (Lanbao) is a quantitative trading research platform built on ROS2 Humble distributed architecture. It provides backtesting, strategy management, risk control, and market data services through a node-based architecture.

## Build System

This is a ROS2 workspace using `colcon` for building. All packages are Python-based ROS2 packages with `setup.py`.

**Build all packages:**
```bash
source /opt/ros/humble/setup.bash
./scripts/build.sh
# Which runs: colcon build --packages-select lanbao_interfaces lanbao_core lanbao_data lanbao_strategy lanbao_backtest lanbao_risk lanbao_monitor --symlink-install
```

**Build a single package:**
```bash
colcon build --packages-select <package_name> --symlink-install
```

**After building, source the install:**
```bash
source install/setup.bash
```

## Running the System

**Start all nodes:**
```bash
./scripts/start_nodes.sh
```

**Stop all nodes:**
```bash
./scripts/stop_nodes.sh
```

**Manual ROS2 launch:**
```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run lanbao_data market_data_node
```

**Docker:**
```bash
docker-compose up -d
```

## Testing

Tests use `pytest` (configured in `pyproject.toml`):

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_data_adapters.py

# Run with verbose output
pytest -v
```

Note: Tests currently use `unittest` style but run via pytest. The test file modifies `sys.path` to include `../src`.

## Linting and Formatting

```bash
# Format code
black .

# Type check
mypy src/

# Lint
flake8 src/
```

Black config: line-length = 100, target Python 3.10+

## Node Architecture

All ROS2 nodes inherit from `LanBaoBaseNode` (`src/lanbao_core/lanbao_core/base_node.py`), which provides:
- Lifecycle management (initialize → start → run → stop)
- Health monitoring via `HealthMonitor`
- Metrics collection via `MetricsCollector`
- Status/alert publishing on ROS2 topics
- QoS profile management
- Retry and timeout helpers

Specialized base classes extend this:
- `DataProcessorNode` — for data collection nodes (market_data_node)
- `StrategyNode` — for strategy execution nodes
- `RiskNode` — for risk control nodes

## Communication Architecture

**Interfaces** (`src/lanbao_interfaces/`) define ROS2 msg/srv/action types:
- Messages: MarketData, StockSignal, TradeSignal, OrderStatus, PortfolioStatus, RiskAlert, BacktestResult, StrategyStatus, NodeStatus
- Services: GetMarketData, ExecuteOrder, RunBacktest, ManageStrategy, CheckRisk, GetNodeStatus
- Actions: BacktestStrategy, DeployStrategy, CircuitBreaker

**Critical PYTHONPATH detail**: The `install/` directories contain `.egg-link` files pointing to `build/` directories. These egg-links are NOT processed when directories are added via `PYTHONPATH` alone. The `start_nodes.sh` script must include both `install/.../site-packages` paths AND `build/<package>` paths in `PYTHONPATH` for imports to work. The build directories contain symlinks to the actual source packages.

## Data Layer Architecture

Market data flows through multiple adapter classes with priority-based fallback:

| Adapter | Priority | Rate Limit | Notes |
|---------|----------|------------|-------|
| `TushareAdapter` | 1 | 0.1s | Primary source, requires `TUSHARE_TOKEN` |
| `AKShareAdapter` | 3 | 3.0s | Free alternative, strict server-side rate limiting |
| `TDXAdapter` | 2 | — | 通达信本地数据 (if available) |
| `MiniQMTAdapter` | 4 | — | QMT量化交易终端 (if available) |

**Data fetch flow** (`_get_data_from_source`):
1. Query local DuckDB cache first
2. If cache miss or empty → try adapters in priority order
3. On successful remote fetch → save to DuckDB (`save_daily_data`)
4. On failure (empty result or exception) → fallback to next adapter

**Important**: `AKShareAdapter._min_interval` is set to **3.0 seconds** to avoid `RemoteDisconnected` errors from server-side rate limiting. Do not lower this value.

Data is persisted to DuckDB via `DuckDBStorage`. The `MarketDataNode` manages adapter lifecycle and data source failover.

## Strategy System

Strategies inherit from `StrategyTemplate` (`src/lanbao_strategy/lanbao_strategy/strategy_template.py`) and implement:
- `analyze(data)` — analyze market data
- `generate_signals(data)` — produce Signal objects (BUY/SELL/HOLD)

The `StrategyFactory` registers and instantiates strategies by template ID. Built-in strategies: `ma_cross`, `rsi`, `macd`.

## Environment Setup

**Python version**: ROS2 Humble is bound to Python 3.10. The `.python-version` file pins `3.10`, and the `.venv` must use Python 3.10. Do not use Python 3.11+ — the `lanbao_interfaces` CMake package builds C extensions (`.so` files) that are ABI-locked to the build-time Python version. If you build with 3.13 and run with 3.10, ROS2 will fail with `UnsupportedTypeSupport` when loading type support libraries.

If `.venv` was created with the wrong Python version:
```bash
rm -rf .venv
uv venv          # uses .python-version (3.10)
uv sync
```

After changing Python versions, **rebuild** `lanbao_interfaces` so its C extensions match:
```bash
rm -rf build/lanbao_interfaces install/lanbao_interfaces
source .venv/bin/activate
source /opt/ros/humble/setup.bash
colcon build --packages-select lanbao_interfaces --symlink-install
```

Required environment variables (see `.env.example`):
- `TUSHARE_TOKEN` — Required for Tushare data source
- `DUCKDB_PATH` — Defaults to `./data/lanbao.duckdb`
- `ROS_DOMAIN_ID` — Defaults to 0
- `LOG_LEVEL` — Defaults to INFO

Install dependencies:
```bash
uv sync
# or for dev:
uv sync --extra dev
```

## Key File Locations

- Configuration: `config/lanbao.yaml`
- Logs: `logs/` (created at runtime)
- Data/DB: `data/lanbao.duckdb`
- Notebooks: `notebooks/01_quick_start.ipynb`, `notebooks/02_multi_data_source_demo.ipynb`
- ROS2 launch files: `src/lanbao_core/launch/`

## Adding a New Strategy

1. Inherit from `StrategyTemplate` in `src/lanbao_strategy/lanbao_strategy/strategy_template.py`
2. Implement `analyze()` and `generate_signals()`
3. Register in `StrategyFactory._register_builtin_strategies()`

## Adding a New ROS2 Node

1. Create package in `src/` with `setup.py`, `package.xml`, and `resource/` directory
2. Inherit from `LanBaoBaseNode` or a specialized subclass
3. Implement `initialize()`, `start()`, `stop()`
4. Add entry point in `setup.py`
5. Add to `scripts/build.sh` and `scripts/start_nodes.sh`
