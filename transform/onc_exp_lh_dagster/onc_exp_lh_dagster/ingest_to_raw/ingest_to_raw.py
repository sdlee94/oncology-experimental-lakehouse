import argparse
import boto3
import json
from io import BytesIO
from datetime import datetime
from pathlib import Path

from onc_exp_lh_dagster.ingest_to_raw import ingest_utils


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Ingest source JSON of simulated ELN data to raw layer")
    parser.add_argument("--dataset", required=True, choices=["experiments", "inventory"])

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
    bucket = config['s3_bucket']
    output_paths = []

    for source_s3_path in source_s3_paths:
        source_s3_key = source_s3_path.split("/", 3)[3]
        print(f"Ingesting detected file {source_s3_key} to raw layer")

        # if config["local"]:
        #     source_file_path = "experiments.json"
        #     records = helpers.load_json_records(source_file_path)

        #     df = helpers.convert_to_df_from_records(records)
        #     df['record_hash'] = df.apply(lambda row: helpers.generate_hash(row.to_dict())['record_hash'], axis=1)

        #     print(df.head(2))

        #     # helpers.write_parquet(df, "experiments.parquet")
        #     # print("Parquet file written locally: experiments.parquet")
        #     continue

        obj = ingest_utils.read_s3(s3_bucket=bucket, s3_key=source_s3_key)
        records = json.loads(obj.read().decode('utf-8'))

        df = ingest_utils.convert_to_df_from_records(records)
        df['record_hash'] = df.apply(lambda row: ingest_utils.generate_hash(row.to_dict())['record_hash'], axis=1)

        # Deduplicate records by filtering out existing experiment ID + record hash pairs
        df["composite_key"] = (
            df["id"] + "|" + df["record_hash"]
        )

        print("check composite_key:", df["composite_key"].head(2))

        existing_keys = ingest_utils.fetch_existing_keys(
            candidate_pairs=df["composite_key"].tolist(),
            database=config["athena_database"],
            table=config["athena_tables"][args.dataset],
            output_location=config["athena_output_location"],
        )

        num_duplicates = df["composite_key"].isin(existing_keys).sum()
        df = df[~df["composite_key"].isin(existing_keys)].copy()
        print(f"Number of duplicate records filtered out: {num_duplicates}")

        df.drop(columns=["composite_key"], inplace=True)

        if df.empty:
            print("No new records to ingest after deduplication. Skipping file.")
            continue

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H-%M-%S")

        output_key = f'raw/{args.dataset}/ingest_date={current_date}/{current_time}.parquet'
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