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

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_merchant_events_topic: str = "cip.merchant.events"
    kafka_merchant_dlq_topic: str = "cip.merchant.events.dlq"
    kafka_shopper_events_topic: str = "cip.shopper.events"
    kafka_shopper_dlq_topic: str = "cip.shopper.events.dlq"
    kafka_campaign_events_topic: str = "cip.campaign.events"
    kafka_campaign_dlq_topic: str = "cip.campaign.events.dlq"
    kafka_product_events_topic: str = "cip.product.events"
    kafka_product_dlq_topic: str = "cip.product.events.dlq"
    kafka_merchant_consumer_group_id: str = "cip-merchant-event-consumer"
    kafka_product_consumer_group_id: str = "cip-product-event-consumer"
    kafka_shopper_consumer_group_id: str = "cip-shopper-event-consumer"
    kafka_campaign_consumer_group_id: str = "cip-campaign-event-consumer"

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

