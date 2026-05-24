import boto3
import botocore
import json
import random
import yaml
from datetime import datetime, timedelta
from typing import Optional


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def load_json_records(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def athena_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def athena_timestamp_or_none(value: Optional[datetime]) -> Optional[str]:
    return athena_timestamp(value) if value else None


# def isoformat(dt: datetime) -> str:
#     return dt.isoformat(timespec="seconds")


# def iso_or_none(value: Optional[datetime]) -> Optional[str]:
#     return value.isoformat(timespec="seconds") if value else None


def random_datetime_between(start: datetime, end: datetime) -> datetime:
    total_seconds = int((end - start).total_seconds())
    offset = random.randint(0, max(total_seconds, 0))
    return start + timedelta(seconds=offset)


def maybe_datetime_after(
    base_dt: datetime,
    probability_present: float,
    max_delay_days: int,
    min_delay_days: int = 1,
) -> Optional[datetime]:
    if random.random() > probability_present:
        return None

    min_seconds = min_delay_days * 24 * 60 * 60
    max_seconds = max_delay_days * 24 * 60 * 60
    seconds = random.randint(min_seconds, max_seconds)
    return base_dt + timedelta(seconds=seconds)


def read_s3(
    s3_bucket: str,
    s3_key: str
) -> "botocore.response.StreamingBody":
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
    return obj["Body"]


def write_to_s3(
    content: str,
    s3_bucket: str | None = None,
    s3_key: str | None = None
) -> None:
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=s3_bucket, 
        Key=s3_key, 
        Body=content.encode("utf-8"), 
        ContentType="application/json"
    )
