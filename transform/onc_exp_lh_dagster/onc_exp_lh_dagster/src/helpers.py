import boto3
import botocore
import json
import random
import time
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


def fetch_existing_hashes(
        candidate_hashes: list[str], 
        database: str, 
        table: str,
        output_location: str,
    ) -> set[str]:
    """
    Query Athena for hashes that already exist in raw table.
    """

    if not candidate_hashes:
        return set()

    athena = boto3.client("athena")

    hash_list = ",".join(f"'{h}'" for h in candidate_hashes)

    query = f"""
        SELECT record_hash
        FROM {database}.{table}
        WHERE record_hash IN ({hash_list})
    """

    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={
            "OutputLocation": output_location
        },
    )

    execution_id = response["QueryExecutionId"]

    while True:
        status = athena.get_query_execution(
            QueryExecutionId=execution_id
        )["QueryExecution"]["Status"]["State"]

        if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break

        time.sleep(1)

    if status != "SUCCEEDED":
        raise Exception("Athena hash lookup failed")

    rows = athena.get_query_results(
        QueryExecutionId=execution_id
    )["ResultSet"]["Rows"]

    existing = set()

    for row in rows[1:]:   # skip header
        existing.add(row["Data"][0]["VarCharValue"])

    return existing

def fetch_existing_keys(
    candidate_pairs: list[tuple[str, str]],
    database: str,
    table: str,
    output_location: str,
) -> set[str]:
    """
    Query Athena for existing (experiment_id, record_hash) combinations.

    Returns:
        set of concatenated keys: "experiment_id|record_hash"
    """

    if not candidate_pairs:
        return set()

    athena = boto3.client("athena")

    # Build composite keys
    composite_keys = [
        f"{exp_id}|{rec_hash}"
        for exp_id, rec_hash in candidate_pairs
    ]

    key_list = ",".join(f"'{k}'" for k in composite_keys)

    query = f"""
        SELECT CONCAT(experiment_id, '|', record_hash) AS composite_key
        FROM "{database}"."{table}"
        WHERE CONCAT(experiment_id, '|', record_hash) IN ({key_list})
    """

    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={
            "OutputLocation": output_location
        },
    )

    execution_id = response["QueryExecutionId"]

    # Wait for completion
    while True:
        execution = athena.get_query_execution(QueryExecutionId=execution_id)["QueryExecution"]
        status = execution["Status"]["State"]   

        if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break

        time.sleep(1)

    if status != "SUCCEEDED":
        reason = execution["Status"].get("StateChangeReason", "Unknown error")
        if ("does not exist" in reason.lower() or 
            "not found" in reason.lower() or 
            "invalid" in reason.lower()):
            # Table or database doesn't exist yet, so no existing keys
            return set()
        raise Exception(f"Athena composite key lookup failed: {reason}")

    rows = athena.get_query_results(
        QueryExecutionId=execution_id
    )["ResultSet"]["Rows"]

    existing = set()

    for row in rows[1:]:  # skip header
        existing.add(row["Data"][0]["VarCharValue"])

    return existing