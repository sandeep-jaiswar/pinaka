from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    s3_endpoint: str = field(
        default_factory=lambda: os.getenv("PINAKA_S3_ENDPOINT", "ministack:4566")
    )
    s3_access_key: str = field(
        default_factory=lambda: os.getenv("PINAKA_AWS_ACCESS_KEY_ID")
        or os.getenv("AWS_ACCESS_KEY_ID", "test")
    )
    s3_secret_key: str = field(
        default_factory=lambda: os.getenv("PINAKA_AWS_SECRET_ACCESS_KEY")
        or os.getenv("AWS_SECRET_ACCESS_KEY", "test")
    )
    s3_region: str = field(
        default_factory=lambda: os.getenv("PINAKA_AWS_REGION", "ap-south-1")
    )
    s3_use_ssl: bool = field(
        default_factory=lambda: os.getenv("PINAKA_S3_USE_SSL", "false") == "true"
    )
    s3_url_style: str = field(
        default_factory=lambda: os.getenv("PINAKA_S3_URL_STYLE", "path")
    )
    bronze_bucket: str = field(
        default_factory=lambda: os.getenv("PINAKA_BRONZE_BUCKET", "pinaka-bronze")
    )
    gold_bucket: str = field(
        default_factory=lambda: os.getenv("PINAKA_GOLD_BUCKET", "pinaka-gold")
    )
    raw_bucket: str = field(
        default_factory=lambda: os.getenv("PINAKA_RAW_BUCKET", "pinaka-raw")
    )
    db_path: str = field(
        default_factory=lambda: os.getenv("PINAKA_DB_PATH", "/tmp/pinaka.duckdb")
    )

    @property
    def s3_http_endpoint(self) -> str:
        return f"http://{self.s3_endpoint}"


settings = Settings()
