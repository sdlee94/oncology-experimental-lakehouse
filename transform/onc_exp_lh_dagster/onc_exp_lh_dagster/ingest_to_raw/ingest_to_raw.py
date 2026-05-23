import argparse
import boto3
import json
from io import BytesIO
from datetime import datetime
from pathlib import Path

from onc_exp_lh_dagster.ingest_to_raw import ingest_utils


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Ingest source JSON of simulated ELN data to raw layer")
    parser.add_argument("--dataset", required=True, choices=["experiments", "samples", "stocks"])

    parser.add_argument(
        "--source_s3_paths",
        action="append",
        required=True,
        help="S3 path to the source JSON file",
    )
    args = parser.parse_args()
    source_s3_paths = args.source_s3_paths

    # Load config from the same directory as this script
    script_dir = Path(__file__).parent
    config_path = script_dir / "config.yaml"
    config = ingest_utils.load_config(config_path)

    s3 = boto3.client('s3')
    bucket = config["s3_bucket"]
    output_paths = []
    for source_s3_path in source_s3_paths:
        source_s3_key = source_s3_path.split("/", 3)[3]
        print(f"Ingesting detected file {source_s3_key} to raw layer")

        obj = ingest_utils.read_s3(s3_bucket=config["s3_bucket"], s3_key=source_s3_key)
        records = json.loads(obj.read().decode('utf-8'))
        print(f"Loaded {len(records)} records from source file")

        df = ingest_utils.convert_to_df_from_records(records)
        print(df.head(2))

        # df['record_hash'] = df.apply(lambda row: ingest_utils.generate_hash(row.to_dict())['record_hash'], axis=1)

        # Deduplicate records by composite key within the incoming batch first
        # df["composite_key"] = df["id"].astype(str) + "|" + df["record_hash"]
        # incoming_count = len(df)
        # df = df.drop_duplicates(subset=["composite_key"]).copy()
        # internal_duplicates = incoming_count - len(df)
        # if internal_duplicates:
        #     print(f"Filtered {internal_duplicates} duplicate records within source payload")

        # if df.empty:
        #     print("No new records to ingest after internal deduplication. Skipping file.")
        #     continue

        # print("check composite_key:", df["composite_key"].head(2))

        # existing_keys = ingest_utils.fetch_existing_keys(
        #     candidate_pairs=df["composite_key"].tolist(),
        #     database=config["athena_database"],
        #     table=config["athena_tables"][args.dataset],
        #     output_location=config["athena_output_location"],
        # )

        # existing_duplicates = df["composite_key"].isin(existing_keys).sum()
        # df = df[~df["composite_key"].isin(existing_keys)].copy()
        # if existing_duplicates:
        #     print(f"Filtered {existing_duplicates} records already present in raw layer")
        # if internal_duplicates or existing_duplicates:
        #     print(f"Total duplicates filtered out: {internal_duplicates + existing_duplicates}")

        # df.drop(columns=["composite_key"], inplace=True)

        # if df.empty:
        #     print("No new records to ingest after deduplication. Skipping file.")
        #     continue

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H-%M-%S")

        output_key = f'raw/{args.dataset}/ingest_date={current_date}/{current_time}.parquet'
        buffer = BytesIO()
        df.to_parquet(buffer, engine='pyarrow', index=False)
        s3.put_object(Bucket=bucket, Key=output_key, Body=buffer.getvalue())

        output_path = f"s3://{bucket}/{output_key}"
        output_paths.append(output_path)
        print(f"Parquet file written to S3: {output_path}")

    # if output_paths:
    #     print("Ingest completed for files:")
    #     for path in output_paths:
    #         print(path)
    # else:
    #     print("No parquet files were written for the provided source paths.")


if __name__ == "__main__":
    main()