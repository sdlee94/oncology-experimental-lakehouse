from collections import defaultdict

from dagster import (
    RunRequest,
    sensor,
    SensorResult,
    SkipReason,
    DefaultSensorStatus,
)
import boto3
import hashlib
import json

s3_client = boto3.client("s3")

DATASET_PREFIXES = {
    "experiments": "ingest/experiments/",
    "samples": "ingest/samples/",
    "stocks": "ingest/stocks/",
    "screening_results": "ingest/screening_results/",
}


@sensor(
    job_name="ingest_to_raw",
    default_status=DefaultSensorStatus.RUNNING,
    minimum_interval_seconds=300,
)
def ingest_sensor(context):
    """Detects new files in S3 datalake ingest layer and triggers ingest to raw script"""

    bucket_name = "oncology-experimental-lakehouse"

    context.log.info("Starting ingest_sensor tick")
    cursor_data = json.loads(context.cursor or "{}")
    processed_files = set(cursor_data.get("processed_files", []))

    new_files_by_dataset = defaultdict(list)

    for dataset, prefix in DATASET_PREFIXES.items():
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".json") and key not in processed_files:
                    new_files_by_dataset[dataset].append(key)

    if not any(new_files_by_dataset.values()):
        context.log.info("No new source files detected")
        return SkipReason("No new source files detected")

    run_requests = []
    for dataset, new_keys in new_files_by_dataset.items():
        if not new_keys:
            continue

        source_s3_paths = [f"s3://{bucket_name}/{key}" for key in sorted(new_keys)]
        batch_key = hashlib.sha256(f"{dataset}|{'|'.join(source_s3_paths)}".encode("utf-8")).hexdigest()

        context.log.info(f"Found {len(new_keys)} new files for dataset '{dataset}'")
        for source_s3_path in source_s3_paths:
            context.log.info(f"Scheduling ingest for {source_s3_path}")

        run_requests.append(
            RunRequest(
                run_key=f"{dataset}-{batch_key}",
                run_config={
                    "ops": {
                        "run_ingest_to_raw": {
                            "config": {
                                "dataset": dataset,
                                "source_s3_paths": source_s3_paths,
                            }
                        }
                    }
                },
                tags={
                    "source_batch": batch_key,
                    "dataset": dataset,
                },
            )
        )

    processed_files.update(
        key for keys in new_files_by_dataset.values() for key in keys
    )
    context.update_cursor(json.dumps({"processed_files": sorted(processed_files)}))

    return SensorResult(run_requests=run_requests)

