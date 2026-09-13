from pydantic import computed_field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Customer Intelligence Platform API"
    environment: str = "development"

    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_user: str = "cip_user"
    postgres_password: str = "cip_password"
    postgres_db: str = "cip_db"

    class Config:
        env_file = ".env"

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

settings = Settings()

