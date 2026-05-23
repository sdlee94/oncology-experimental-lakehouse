from dagster import (
    OpExecutionContext,
    op,
    Out,
    graph
)
import os
import subprocess
import sys
from datetime import datetime
import boto3
from botocore.exceptions import ClientError


INGEST_SCRIPT_PATH = "onc_exp_lh_dagster.ingest_to_raw.ingest_to_raw"

def _run_ingest_to_raw(context: OpExecutionContext, dataset: str, source_s3_paths: list[str]) -> dict:
    if not isinstance(source_s3_paths, list):
        source_s3_paths = [source_s3_paths]

    args = [sys.executable, "-m", INGEST_SCRIPT_PATH, "--dataset", dataset]
    for source_s3_path in source_s3_paths:
        args.extend(["--source_s3_paths", source_s3_path])

    try:
        result = subprocess.run(
            args,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        context.log.error(f"Subprocess failed with return code {e.returncode}")
        context.log.error(f"STDOUT: {e.stdout}")
        context.log.error(f"STDERR: {e.stderr}")
        raise e

    if result.stdout:
        context.log.info(f"Ingest subprocess output:\n{result.stdout.strip()}")
    if result.stderr:
        context.log.warning(f"Ingest subprocess stderr:\n{result.stderr.strip()}")

    output_lines = result.stdout.strip().split("\n")
    s3_paths = []
    for line in output_lines:
        if line.strip().startswith("Parquet file written to S3:"):
            s3_path = line.split("s3://", 1)[-1].strip()
            s3_paths.append(f"s3://{s3_path}")

    if not s3_paths:
        raise ValueError("Could not extract any S3 output paths from ingest output")

    return {
        "dataset": dataset,
        "s3_paths": s3_paths,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
    }


@op(
    description="Run the shared ingest script for any dataset source files",
    config_schema={
        "dataset": str,
        "source_s3_paths": list,
    },
    out=Out(
        dict,
        description="S3 path and metadata of ingested file"
    )
)
def run_ingest_to_raw(context) -> dict:
    dataset = context.op_config["dataset"]
    source_s3_paths = context.op_config["source_s3_paths"]
    
    return _run_ingest_to_raw(context, dataset, source_s3_paths)


@op(
    description="Trigger AWS Glue crawler to update Athena table metadata",
)
def trigger_glue_crawler(context, ingest_metadata: dict) -> dict:
    """Trigger Glue crawler after data is ingested"""
    dataset = ingest_metadata["dataset"]
    glue_client = boto3.client('glue')
    
    crawler_name = f"raw_{dataset}"

    try:
        # context.log.info(f"Triggering Glue crawler: {crawler_name}")
        response = glue_client.start_crawler(Name=crawler_name)
        
        context.log.info(f"✅ Crawler triggered successfully: {crawler_name}")
        
        return {
            "crawler_name": crawler_name,
            "status": "triggered",
            "ingest_path": ingest_metadata["s3_paths"],
            "triggered_at": datetime.now().isoformat(),
        }
        
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"].get("Message", "")
        if error_code == "CrawlerRunningException" or "already started" in error_message.lower():
            context.log.info(f"Crawler '{crawler_name}' is already running; skipping start.")
            return {
                "crawler_name": crawler_name,
                "status": "already_running",
                "ingest_path": ingest_metadata["s3_paths"],
                "triggered_at": datetime.now().isoformat(),
            }
        context.log.error(f"❌ Failed to trigger crawler: {error_code}: {error_message}")
        raise
    except Exception as e:
        context.log.error(f"❌ Failed to trigger crawler: {str(e)}")
        raise


@op(
    description="Validate that Athena can query the new data",
)
def validate_athena_access(context, crawler_result: dict) -> dict:
    """Verify Athena can query the updated table"""
    athena_client = boto3.client('athena', region_name='us-east-1')
    
    try:
        # Query the latest partition
        query = """
        SELECT COUNT(*) as record_count
        FROM oncology.experiments
        WHERE ingest_date = CAST(CURRENT_DATE AS VARCHAR)
        LIMIT 1
        """
        
        athena_results_location = f's3://oncology-experimental-lakehouse/athena-results/'
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': 'oncology'},
            ResultConfiguration={'OutputLocation': athena_results_location}
        )
        
        query_execution_id = response['QueryExecutionId']
        context.log.info(f"Athena query started")
        
        return {
            "query_execution_id": query_execution_id,
            "status": "query_submitted",
            "validation_time": datetime.now().isoformat(),
        }
        
    except Exception as e:
        context.log.error(f"Athena validation failed: {str(e)}")
        raise


@graph
def ingest_to_raw():
    """Complete pipeline: Ingest → Glue Crawl → Athena Validation"""
    ingest_result = run_ingest_to_raw()
    crawler_result = trigger_glue_crawler(ingest_result)
    athena_result = validate_athena_access(crawler_result)
    return athena_result