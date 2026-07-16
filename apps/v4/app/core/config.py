from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "社交媒体及网络直播监测与溯源系统"
    environment: str = "development"
    admin_api_key: str = ""
    database_url: str = "sqlite:///./data/monitor.db"
    storage_root: Path = Path("./data/storage")
    detector_base_url: str = "http://127.0.0.1:8080"
    detector_enabled: bool = False
    push_enabled: bool = False
    push_events_url: str = ""
    push_media_url: str = ""
    push_bearer_token: str = ""
    push_target_name: str = "赵帅项目方"
    live_monitor_bridge_url: str = ""
    live_monitor_bridge_token: str = ""
    legacy_douyin_api_url: str = ""
    legacy_douyin_output_root: Path = Path("/data/comment-backend-douyin-live/output/douyin_live_dataset")
    legacy_douyin_max_rounds: int = 1
    legacy_douyin_max_workers: int = 1
    legacy_douyin_sync_interval_seconds: int = 15
    legacy_douyin_sync_max_checks: int = 40
    anonymization_salt: str = "replace-this-in-production"
    default_segment_seconds: int = 120
    http_timeout_seconds: int = 60
    douyin_connector_url: str = ""
    douyin_connector_token: str = ""
    kuaishou_connector_url: str = ""
    kuaishou_connector_token: str = ""
    demo_provider_enabled: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
settings.storage_root.mkdir(parents=True, exist_ok=True)
Path("./data/logs").mkdir(parents=True, exist_ok=True)
