import boto3
import hashlib
import json
import pandas as pd
from io import BytesIO
from pathlib import Path
from datetime import datetime

import helpers


def flatten_record(record: dict) -> dict:
    experiment = record.get("experiment", {})
    people = record.get("people", {})
    protocol = record.get("protocol", {})
    timestamps = record.get("timestamps", {})

    return {
        "experiment_id": experiment.get("id"),
        "project": experiment.get("project"),
        "experiment_name": experiment.get("name"),
        "status": experiment.get("status"),
        "run_date": experiment.get("run_date"),
        "author": people.get("author"),
        "witnessed_by": people.get("witnessed_by"),
        "protocol_name": protocol.get("name"),
        "protocol_code": protocol.get("code"),
        "protocol_version": protocol.get("version"),
        "created_at": timestamps.get("created_at"),
        "signed_at": timestamps.get("signed_at"),
        "witnessed_at": timestamps.get("witnessed_at"),
    }


def convert_to_dataframe_from_records(records: list[dict]) -> pd.DataFrame:
    rows = [flatten_record(record) for record in records]
    df = pd.DataFrame(rows)

    # datetime_cols = [
    #     "run_date",
    #     "created_at",
    #     "signed_at",
    #     "witnessed_at",
    # ]

    # for col in datetime_cols:
    #     if col in df.columns:
    #         print(type(col))
            # df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def generate_hash(record: dict) -> dict:
    # deterministic hash from normalized record payload
    canonical_json = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )

    record_hash = hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()

    return {
        "record_hash": record_hash,
    }


def build_source_file_metadata(source_file_path: str) -> dict:
    path = Path(source_file_path)
    source_file_name = path.name

    # extract run_date=YYYY-MM-DD from path
    source_file_run_date = None
    for part in path.parts:
        if part.startswith("run_date="):
            source_file_run_date = part.split("=", 1)[1]
            break

    return {
        "source_file_name": source_file_name,
        "source_file_path": source_file_path,
        "source_file_run_date": source_file_run_date,
    }


def enrich_with_raw_metadata(df: pd.DataFrame, records: list[dict], source_file_path: str) -> pd.DataFrame:
    """
    Generate raw metadata for each record and append as new columns to the DataFrame.
    """
    # Generate source-file metadata once
    source_metadata = build_source_file_metadata(source_file_path)
    
    # Generate per-record metadata (record_hash)
    record_metadata_list = [generate_hash(record) for record in records]
    record_metadata_df = pd.DataFrame(record_metadata_list)
    
    # Add source-file metadata columns (broadcast to all rows)
    for key, value in source_metadata.items():
        record_metadata_df[key] = value
    
    # Concatenate the metadata columns with the original DataFrame
    df = pd.concat([df.reset_index(drop=True), record_metadata_df.reset_index(drop=True)], axis=1)
    
    # Add ingestion timestamp
    df["ingested_at"] = datetime.now()
    
    return df


def write_parquet(df: pd.DataFrame, output_file: str) -> None:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(
        output_path,
        engine="pyarrow",
        index=False,
    )


def main() -> None:
    config = helpers.load_config()
    config = config["raw"]["experiments"]

    if config["local"]:
        source_file_path = "experiments.json"
        records = helpers.load_json_records(source_file_path)

        df = convert_to_dataframe_from_records(records)
        # df = enrich_with_raw_metadata(df, records, source_file_path)
        # write_parquet(df, "experiments.parquet")
        # print("Parquet file written locally: experiments.parquet")

    else:
        s3 = boto3.client('s3')
        bucket = config['s3_bucket']

        obj = helpers.read_s3(s3_bucket=bucket, s3_key=config["test_source"])
        records = json.loads(obj.read().decode('utf-8'))

        df = convert_to_dataframe_from_records(records)
        # df = enrich_with_raw_metadata(df, records, config["test_source"])

        # Write to S3
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H-%M-%S")

        output_key = f'raw/experiments/ingest_date={current_date}/{current_time}.parquet'
        buffer = BytesIO()
        df.to_parquet(buffer, engine='pyarrow', index=False)
        s3.put_object(Bucket=bucket, Key=output_key, Body=buffer.getvalue())
        print(f"Parquet file written to S3: s3://{bucket}/{output_key}")


if __name__ == "__main__":
    main()