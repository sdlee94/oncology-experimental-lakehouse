from dagster import Definitions
from dagster_dbt import DbtCliResource

from .ops import ingest_to_raw
from .ingest_to_raw.sensor import ingest_sensor
from .assets import onc_exp_lh_dbt_assets
from .project import onc_exp_lh_project
from .schedules import schedules

defs = Definitions(
    assets=[onc_exp_lh_dbt_assets],
    jobs=[ingest_to_raw.to_job()],
    sensors=[ingest_sensor],
    schedules=schedules,
    resources={
        "dbt": DbtCliResource(project_dir=onc_exp_lh_project),
    },
)