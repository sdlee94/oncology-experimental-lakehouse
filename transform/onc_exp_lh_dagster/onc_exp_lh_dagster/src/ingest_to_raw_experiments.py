import argparse
import boto3
import hashlib
import json
import pandas as pd
import time
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

    print(f"Found {len(existing)} existing records in Athena")

    return existing


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
    parser.add_argument(
        "--source_s3_path",
        action="append",
        required=True,
        help="S3 path to the source JSON file",
    )
    args = parser.parse_args()
    source_s3_paths = args.source_s3_path

    config = helpers.load_config("config.yaml")
    config = config["raw"]["experiments"]

    s3 = boto3.client('s3')
    bucket = config['s3_bucket']
    output_paths = []

    for source_s3_path in source_s3_paths:
        source_s3_key = source_s3_path.split("/", 3)[3]
        print(f"Ingesting detected file {source_s3_key} to raw layer")

        if config["local"]:
            source_file_path = "experiments.json"
            records = helpers.load_json_records(source_file_path)

            df = convert_to_dataframe_from_records(records)
            df['record_hash'] = df.apply(lambda row: generate_hash(row.to_dict())['record_hash'], axis=1)

            print(df.head(2))

            # write_parquet(df, "experiments.parquet")
            # print("Parquet file written locally: experiments.parquet")
            continue

        obj = helpers.read_s3(s3_bucket=bucket, s3_key=source_s3_key)
        records = json.loads(obj.read().decode('utf-8'))

        df = convert_to_dataframe_from_records(records)
        df['record_hash'] = df.apply(lambda row: generate_hash(row.to_dict())['record_hash'], axis=1)

        # Deduplicate records by filtering out existing experiment ID + record hash pairs
        df["composite_key"] = (
            df["experiment_id"] + "|" + df["record_hash"]
        )

        existing_keys = fetch_existing_keys(
            candidate_pairs=df["composite_key"].tolist(),
            database=config["athena_database"],
            table=config["athena_table"],
            output_location=config["athena_output_location"],
        )

        df = df[~df["composite_key"].isin(existing_keys)].copy()
        print(f"Number of duplicate records filtered out: {len(df) - len(existing_keys)}")

        df.drop(columns=["composite_key"], inplace=True)

        if df.empty:
            print("No new records to ingest after deduplication. Skipping file.")
            continue

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H-%M-%S")

        output_key = f'raw/experiments/ingest_date={current_date}/{current_time}.parquet'
        buffer = BytesIO()
        df.to_parquet(buffer, engine='pyarrow', index=False)
        s3.put_object(Bucket=bucket, Key=output_key, Body=buffer.getvalue())

        output_path = f"s3://{bucket}/{output_key}"
        output_paths.append(output_path)
        print(f"Parquet file written to S3: {output_path}")

    if output_paths:
        print("Ingest completed for files:")
        for path in output_paths:
            print(path)
    else:
        print("No parquet files were written for the provided source paths.")


if __name__ == "__main__":
    main()