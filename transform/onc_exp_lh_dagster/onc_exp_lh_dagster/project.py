from pathlib import Path

from dagster_dbt import DbtProject

onc_exp_lh_project = DbtProject(
    project_dir=Path(__file__).joinpath("..", "..", "..", "onc_exp_lh").resolve(),
    packaged_project_dir=Path(__file__).joinpath("..", "..", "dbt-project").resolve(),
)
onc_exp_lh_project.prepare_if_dev()