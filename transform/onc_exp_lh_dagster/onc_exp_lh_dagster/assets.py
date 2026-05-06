from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets

from .project import onc_exp_lh_project


@dbt_assets(manifest=onc_exp_lh_project.manifest_path)
def onc_exp_lh_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
    