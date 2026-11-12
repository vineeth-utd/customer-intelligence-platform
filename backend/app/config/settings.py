from typing import Self
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, computed_field, model_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Customer Intelligence Platform API"
    environment: str = "development"
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    auth_secret_key: str = "dev-insecure-secret-key-change-in-production"
    auth_token_expire_minutes: int = 1440

    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_user: str = "cip_user"
    postgres_password: str = "cip_password"
    postgres_db: str = "cip_db"
    postgres_test_db: str = "cip_test_db"
    test_database_url_override: str | None = Field(
        default=None,
        validation_alias=AliasChoices("test_database_url", "test_database_url_override"),
    )

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_merchant_events_topic: str = "cip.merchant.events"
    kafka_merchant_dlq_topic: str = "cip.merchant.events.dlq"
    kafka_shopper_events_topic: str = "cip.shopper.events"
    kafka_shopper_dlq_topic: str = "cip.shopper.events.dlq"
    kafka_campaign_events_topic: str = "cip.campaign.events"
    kafka_campaign_dlq_topic: str = "cip.campaign.events.dlq"
    kafka_product_events_topic: str = "cip.product.events"
    kafka_product_dlq_topic: str = "cip.product.events.dlq"
    kafka_default_partitions: int = 1
    kafka_default_replication_factor: int = 1
    kafka_consumer_max_poll_interval_ms: int = 300000
    kafka_consumer_max_poll_records: int = 100
    kafka_consumer_session_timeout_ms: int = 30000
    kafka_consumer_heartbeat_interval_ms: int = 10000
    kafka_merchant_consumer_group_id: str = "cip-merchant-event-consumer"
    kafka_product_consumer_group_id: str = "cip-product-event-consumer"
    kafka_shopper_consumer_group_id: str = "cip-shopper-event-consumer"
    kafka_campaign_consumer_group_id: str = "cip-campaign-event-consumer"

    reference_resolution_timeout_seconds: float = 30.0
    reference_resolution_interval_seconds: float = 0.5

    merchant_generator_population_size: int = 50
    merchant_generator_tick_interval_seconds: float = 5.0
    merchant_generator_seed: int | None = None

    product_generator_products_per_merchant: int = 5
    product_generator_variants_per_product: int = 3
    product_generator_tick_interval_seconds: float = 5.0
    product_generator_seed: int | None = None

    enable_background_scheduler: bool = True
    analytics_job_cron_minute: str = "15"
    analytics_job_lookback_days: int = 1
    merchant_profile_job_interval_minutes: int = 15
    shopper_profile_job_interval_minutes: int = 15
    shopper_journey_job_interval_minutes: int = 15
    merchant_journey_job_interval_minutes: int = 15
    shopper_segment_membership_job_interval_minutes: int = 15
    merchant_health_job_interval_minutes: int = 15
    journey_max_window_days: int = 7

    class Config:
        env_file = ".env"

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def test_database_url(self) -> str:
        if self.test_database_url_override:
            return self.test_database_url_override
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_test_db}"
        )

    @model_validator(mode="after")
    def validate_test_database_configuration(self) -> Self:
        if not self.postgres_test_db or not self.postgres_test_db.strip():
            raise ValueError("postgres_test_db must not be empty.")
        if self.postgres_test_db == self.postgres_db:
            raise ValueError(
                f"postgres_test_db ('{self.postgres_test_db}') cannot be identical to postgres_db ('{self.postgres_db}')."
            )
        parsed = urlparse(self.test_database_url)
        target_db = parsed.path.lstrip("/")
        if not target_db:
            raise ValueError("test_database_url must specify a target database.")
        if target_db == self.postgres_db:
            raise ValueError(
                f"test_database_url points to the application database '{self.postgres_db}'. "
                f"Automated tests must run against a dedicated test database (e.g. '{self.postgres_test_db}')."
            )
        return self

settings = Settings()

