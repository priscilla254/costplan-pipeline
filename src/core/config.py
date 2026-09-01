from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    sql_server_connection_string: str
    landing_dir: str = "data/landing"
    process_adjustments: bool = False


settings = Settings()
