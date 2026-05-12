import yaml
from pathlib import Path
from fastapi import APIRouter

from ..models import SystemConfig

router = APIRouter()

CONFIG_PATH = Path("config/settings.yaml")


def _load_config() -> SystemConfig:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return SystemConfig(**data) if data else SystemConfig()
    return SystemConfig()


def _save_config(config: SystemConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(), f, allow_unicode=True, default_flow_style=False)


@router.get("/config", response_model=SystemConfig)
async def get_config():
    return _load_config()


@router.put("/config", response_model=SystemConfig)
async def update_config(config: SystemConfig):
    _save_config(config)
    return config
