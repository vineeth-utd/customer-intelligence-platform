from app.config.settings import Settings


def test_kafka_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "broker-1:9092")
    monkeypatch.setenv("KAFKA_MERCHANT_EVENTS_TOPIC", "test.merchant.events")

    test_settings = Settings(_env_file=None)

    assert test_settings.kafka_bootstrap_servers == "broker-1:9092"
    assert test_settings.kafka_merchant_events_topic == "test.merchant.events"


def test_kafka_settings_defaults():
    test_settings = Settings(_env_file=None)

    assert test_settings.kafka_bootstrap_servers == "localhost:9092"
    assert test_settings.kafka_merchant_events_topic == "cip.merchant.events"
    assert test_settings.kafka_shopper_events_topic == "cip.shopper.events"
    assert test_settings.kafka_campaign_events_topic == "cip.campaign.events"
