import boto3
import hashlib
import json
import random
import time
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional


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


def write_parquet(df: pd.DataFrame, output_file: str) -> None:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(
        output_path,
        engine="pyarrow",
        index=False,
    )


def read_s3(
    s3_bucket: str,
    s3_key: str
) -> "boto3.response.StreamingBody":
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
    return obj["Body"]


def flatten_dict(obj: Any, parent_key: str = "", sep: str = "_") -> dict[str, Any]:
    items: dict[str, Any] = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            items.update(flatten_dict(value, key, sep))
    elif isinstance(obj, list):
        for value in obj:
            items.update(flatten_dict(value, parent_key, sep))
    else:
        if parent_key:
            items[parent_key] = obj

    return items


def convert_to_df_from_records(records: list[dict]) -> pd.DataFrame:
    rows = [flatten_dict(record) for record in records]
    df = pd.DataFrame(rows)

    return df


# def generate_hash(record: dict) -> dict:
#     # deterministic hash from normalized record payload
#     canonical_json = json.dumps(
#         record,
#         sort_keys=True,
#         separators=(",", ":"),
#         ensure_ascii=False
#     )

#     record_hash = hashlib.sha256(
#         canonical_json.encode("utf-8")
#     ).hexdigest()[:12]

#     return {
#         "record_hash": record_hash,
#     }


# def fetch_existing_keys(
#     candidate_pairs: list[str],
#     database: str,
#     table: str,
#     output_location: str,
# ) -> set[str]:
#     """
#     Query Athena for existing composite keys.

#     Args:
#         candidate_pairs: list of composite keys in the form "id|record_hash"
#         database: Athena database name
#         table: Athena table name
#         output_location: S3 query result location

#     Returns:
#         set of existing composite keys
#     """

#     if not candidate_pairs:
#         return set()

#     athena = boto3.client("athena")
#     candidate_pairs = list(dict.fromkeys(candidate_pairs))
#     key_list = ",".join(f"'{k}'" for k in candidate_pairs)

#     query = f"""
#         SELECT CONCAT(id, '|', record_hash) AS composite_key
#         FROM "{database}"."{table}"
#         WHERE CONCAT(id, '|', record_hash) IN ({key_list})
#     """

#     response = athena.start_query_execution(
#         QueryString=query,
#         QueryExecutionContext={"Database": database},
#         ResultConfiguration={
#             "OutputLocation": output_location
#         },
#     )

#     execution_id = response["QueryExecutionId"]

#     # Wait for completion
#     while True:
#         execution = athena.get_query_execution(QueryExecutionId=execution_id)["QueryExecution"]
#         status = execution["Status"]["State"]   

#         if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
#             break

#         time.sleep(1)

#     if status != "SUCCEEDED":
#         reason = execution["Status"].get("StateChangeReason", "Unknown error")
#         if ("does not exist" in reason.lower() or 
#             "not found" in reason.lower() or 
#             "invalid" in reason.lower()):
#             # Table or database doesn't exist yet, so no existing keys
#             return set()
#         raise Exception(f"Athena composite key lookup failed: {reason}")

#     rows = athena.get_query_results(
#         QueryExecutionId=execution_id
#     )["ResultSet"]["Rows"]

#     existing = set()

#     for row in rows[1:]:  # skip header
#         existing.add(row["Data"][0]["VarCharValue"])

#     print(f"Found {len(existing)} existing records in Athena")

#     return existing