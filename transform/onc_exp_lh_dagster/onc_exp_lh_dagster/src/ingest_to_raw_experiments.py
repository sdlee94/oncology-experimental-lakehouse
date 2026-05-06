import boto3
import hashlib
import json
import pandas as pd
from io import BytesIO
from pathlib import Path
from datetime import datetime
import argparse

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
    ).hexdigest()[:12]

    return {
        "record_hash": record_hash,
    }


def write_parquet(df: pd.DataFrame, output_file: str) -> None:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(
        output_path,
        engine="pyarrow",
        index=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest experiments to raw layer")
    parser.add_argument("--source_s3_path", required=True, help="S3 path to the source JSON file")
    args = parser.parse_args()
    source_s3_key = args.source_s3_path.split("/", 3)[3]
    print(f"Ingesting detected file {source_s3_key} to raw layer")


    config = helpers.load_config("config.yaml")
    config = config["raw"]["experiments"]

    if config["local"]:
        source_file_path = "experiments.json"
        records = helpers.load_json_records(source_file_path)

        df = convert_to_dataframe_from_records(records)
        df['record_hash'] = df.apply(lambda row: generate_hash(row.to_dict())['record_hash'], axis=1)
  
        print(df.head(2))

        # write_parquet(df, "experiments.parquet")
        # print("Parquet file written locally: experiments.parquet")

    else:
        s3 = boto3.client('s3')
        bucket = config['s3_bucket']

        obj = helpers.read_s3(s3_bucket=bucket, s3_key=source_s3_key)
        records = json.loads(obj.read().decode('utf-8'))

        df = convert_to_dataframe_from_records(records)
        df['record_hash'] = df.apply(lambda row: generate_hash(row.to_dict())['record_hash'], axis=1)

        candidate_keys = list(
            zip(df["experiment_id"], df["record_hash"])
        )

        existing_keys = helpers.fetch_existing_keys(
            candidate_pairs=candidate_keys,
            database=config["athena_database"],
            table=config["athena_table"],
            output_location=config["athena_output_location"],
        )

        # Deduplicate records by filtering out existing experiment ID + record hash pairs
        df["composite_key"] = (
            df["experiment_id"] + "|" + df["record_hash"]
        )

        df = df[~df["composite_key"].isin(existing_keys)].copy()
        print(f"Number of duplicate records filtered out: {len(df) - len(existing_keys)}")

        df.drop(columns=["composite_key"], inplace=True)

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