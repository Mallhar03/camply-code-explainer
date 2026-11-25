from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://camply:camply@localhost:5433/camply_explainer"
    gemini_api_key: str = ""
    llm_model: str = "gemini-3.8-flash"
    repo_root: Path = Path("/home/mallhar/Desktop/camply")
    sim_threshold: float = 0.45


settings = Settings()
