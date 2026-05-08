from dagster import (
    RunRequest,
    sensor,
    SensorResult,
    SkipReason,
    DefaultSensorStatus,
    asset_sensor,
)
import boto3
import hashlib
import json
from datetime import datetime

s3_client = boto3.client("s3")


@sensor(
    job_name="ingest_and_crawl_pipeline",
    default_status=DefaultSensorStatus.RUNNING,
    minimum_interval_seconds=300,
    description="Monitors S3 for new parquet files in source location",
)
def s3_parquet_sensor(context):
    """Detects new parquet files in S3 and triggers ingest to raw script"""
    
    bucket_name = "oncology-experimental-lakehouse"
    prefix = "ingest/experiments/"
    
    # Load previous state
    cursor_data = json.loads(context.cursor or "{}")
    processed_files = set(cursor_data.get("processed_files", []))
    
    try:
        # List objects in S3
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        new_files = []
        current_files = set()
        
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".json"):
                    current_files.add(key)
                    if key not in processed_files:
                        new_files.append(key)
        
        if not new_files:
            return SkipReason("No new source files detected")
        
        context.log.info(f"Found {len(new_files)} new source files")

        source_s3_paths = [f"s3://{bucket_name}/{key}" for key in sorted(new_files)]
        for source_s3_path in source_s3_paths:
            context.log.info(f"Scheduling ingest for {source_s3_path}")

        batch_key = hashlib.sha256("|".join(source_s3_paths).encode("utf-8")).hexdigest()
        run_requests = [
            RunRequest(
                run_key=batch_key,
                run_config={
                    "ops": {
                        "run_ingest_experiments": {
                            "config": {
                                "source_s3_paths": source_s3_paths
                            }
                        }
                    }
                },
                tags={
                    "source_batch": batch_key,
                    "dataset": "experiments",
                },
            )
        ]

        # Update cursor with files that we have scheduled for ingest
        processed_files.update(new_files)
        context.update_cursor(
            json.dumps(
                {
                    "processed_files": sorted(processed_files),
                }
            )
        )

        return SensorResult(
            run_requests=run_requests
        )
        
    except Exception as e:
        context.log.error(f"S3 sensor failed: {e}")
        raise