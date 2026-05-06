from dagster import Definitions
from dagster_dbt import DbtCliResource

from .ops import ingest_and_crawl_pipeline
from .sensors import s3_parquet_sensor
from .assets import onc_exp_lh_dbt_assets
from .project import onc_exp_lh_project
from .schedules import schedules

defs = Definitions(
    assets=[onc_exp_lh_dbt_assets],
    jobs=[ingest_and_crawl_pipeline.to_job()],
    sensors=[s3_parquet_sensor],
    schedules=schedules,
    resources={
        "dbt": DbtCliResource(project_dir=onc_exp_lh_project),
    },
)