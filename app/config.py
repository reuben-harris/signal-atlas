from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CELLULAR_TOPIC_NAMES = (
    "gsm_message",
    "cdma_message",
    "umts_message",
    "lte_message",
    "nr_message",
)
DEFAULT_DATABASE_URL = (
    "postgres://network_survey:network_survey@localhost:15432/network_survey"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    mqtt_host: str = Field("localhost", alias="MQTT_HOST")
    mqtt_port: int = Field(1883, alias="MQTT_PORT")
    mqtt_tls: bool = Field(False, alias="MQTT_TLS")
    mqtt_client_id: str = Field(
        "accessatlas-network-survey-ingestor",
        alias="MQTT_CLIENT_ID",
    )
    mqtt_username: str = Field("", alias="MQTT_USERNAME")
    mqtt_password: str = Field("", alias="MQTT_PASSWORD")
    mqtt_topic_prefix_raw: str = Field("", alias="MQTT_TOPIC_PREFIX")
    mqtt_qos: int = Field(1, alias="MQTT_QOS")
    mqtt_keepalive_seconds: int = Field(60, alias="MQTT_KEEPALIVE_SECONDS")
    database_url: str = Field(DEFAULT_DATABASE_URL, alias="DATABASE_URL")
    debug: bool = Field(False, alias="DEBUG")

    @field_validator("mqtt_qos")
    @classmethod
    def validate_mqtt_qos(cls, value: int) -> int:
        if value not in {0, 1, 2}:
            raise ValueError("MQTT_QOS must be 0, 1, or 2")
        return value

    @property
    def mqtt_topic_prefix(self) -> str:
        prefix = self.mqtt_topic_prefix_raw.strip().strip("/")
        if not prefix:
            return ""
        return f"{prefix}/"

    def topic_with_prefix(self, topic_name: str) -> str:
        return f"{self.mqtt_topic_prefix}{topic_name}"

    @property
    def cellular_topics(self) -> list[str]:
        return [
            self.topic_with_prefix(topic_name) for topic_name in CELLULAR_TOPIC_NAMES
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
