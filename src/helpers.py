import random
from datetime import datetime, timedelta
from typing import Optional


def iso_or_none(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat(timespec="seconds") if value else None


def random_datetime_between(start: datetime, end: datetime) -> datetime:
    total_seconds = int((end - start).total_seconds())
    offset = random.randint(0, max(total_seconds, 0))
    return start + timedelta(seconds=offset)


def isoformat(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


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


def write_to_s3(
    content: str,
    s3_bucket: str | None = None,
    s3_key: str | None = None
) -> None:
    import boto3

    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=s3_bucket, 
        Key=s3_key, 
        Body=content.encode("utf-8"), 
        ContentType="application/json"
    )
