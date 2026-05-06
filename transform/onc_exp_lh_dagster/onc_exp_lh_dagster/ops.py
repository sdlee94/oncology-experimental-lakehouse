from dagster import (
    op,
    Out,
    DynamicOut,
    DynamicOutput,
    graph
)
import os
import subprocess
import sys
from datetime import datetime
import json
import boto3


@op(
    description="Run the ingest script to load experiments from S3 ingest to raw layer",
    config_schema={"source_s3_path": str},
    out=Out(
        dict,
        description="S3 path and metadata of ingested parquet file"
    )
)
def run_ingest_experiments(context) -> dict:
    """Execute the Python ingest script"""
    try:
        source_s3_path = context.op_config["source_s3_path"]

        # Run the ingest script
        result = subprocess.run(
            [
                sys.executable,
                "onc_exp_lh_dagster/src/ingest_to_raw_experiments.py",
                "--source_s3_path", source_s3_path,
            ],
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            check=True,
        )
        
        context.log.info(f"Ingest completed: {result.stdout}")
        
        # Parse the output to get the S3 path
        # Format: "Parquet file written to S3: s3://{bucket}/{output_key}"
        output_lines = result.stdout.strip().split('\n')
        s3_path = None
        for line in output_lines:
            if "s3://" in line:
                s3_path = line.split("s3://")[-1]
                break
        
        if not s3_path:
            raise ValueError("Could not extract S3 path from ingest output")
        
        return {
            "s3_path": f"s3://{s3_path}",
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }
        
    except subprocess.CalledProcessError as e:
        context.log.error(f"Ingest script failed with exit code {e.returncode}")
        context.log.error(f"STDOUT:\n{e.stdout}")
        context.log.error(f"STDERR:\n{e.stderr}")
        raise


@op(
    description="Trigger AWS Glue crawler to update Athena table metadata",
)
def trigger_glue_crawler(context, ingest_metadata: dict) -> dict:
    """Trigger Glue crawler after data is ingested"""
    glue_client = boto3.client('glue')
    
    crawler_name = "raw_experiments"

    try:
        context.log.info(f"Triggering Glue crawler: {crawler_name}")
        response = glue_client.start_crawler(Name=crawler_name)
        
        context.log.info(f"✅ Crawler triggered: {response['ResponseMetadata']['HTTPHeaders']['x-amzn-requestid']}")
        
        return {
            "crawler_name": crawler_name,
            "status": "triggered",
            "ingest_path": ingest_metadata["s3_path"],
            "triggered_at": datetime.now().isoformat(),
        }
        
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
        context.log.info(f"Athena query started: {query_execution_id}")
        
        return {
            "query_execution_id": query_execution_id,
            "status": "query_submitted",
            "validation_time": datetime.now().isoformat(),
        }
        
    except Exception as e:
        context.log.error(f"Athena validation failed: {str(e)}")
        raise


@graph
def ingest_and_crawl_pipeline():
    """Complete pipeline: Ingest → Glue Crawl → Athena Validation"""
    ingest_result = run_ingest_experiments()
    crawler_result = trigger_glue_crawler(ingest_result)
    athena_result = validate_athena_access(crawler_result)
    return athena_result