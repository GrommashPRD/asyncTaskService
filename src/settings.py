from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    RABBIT_HOST: str
    RABBIT_PORT: int
    RABBIT_USER: str
    RABBIT_PASS: str
    RABBIT_VHOST: str

    TASK_QUEUE_NAME: str
    TASK_QUEUE_MAX_PRIORITY: int

    model_config = SettingsConfigDict(
        env_file=".env.example",
        env_file_encoding="utf-8",
    )


settings = Settings()
