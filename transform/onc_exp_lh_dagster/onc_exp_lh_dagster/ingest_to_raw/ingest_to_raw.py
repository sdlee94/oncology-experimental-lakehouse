import argparse
import boto3
import json
from io import BytesIO
from datetime import datetime
from pathlib import Path

from onc_exp_lh_dagster.ingest_to_raw import ingest_utils


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Ingest source JSON of simulated ELN data to raw layer")
    parser.add_argument("--dataset", required=True, choices=["experiments", "samples", "stocks", "screening_results"])

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

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H-%M-%S")

        output_key = f'raw/{args.dataset}/ingest_date={current_date}/{current_time}.parquet'
        buffer = BytesIO()
        df.to_parquet(buffer, engine='pyarrow', index=False)
        s3.put_object(Bucket=bucket, Key=output_key, Body=buffer.getvalue())

        output_path = f"s3://{bucket}/{output_key}"
        output_paths.append(output_path)
        print(f"Parquet file written to S3: {output_path}")


if __name__ == "__main__":
    main()