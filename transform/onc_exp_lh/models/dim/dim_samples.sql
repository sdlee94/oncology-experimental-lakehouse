{{ config(
    materialized='incremental',
    table_type='iceberg',
    unique_key='sample_id',
    incremental_strategy='merge',
    external_location='s3://oncology-experimental-lakehouse/curate/dim_samples/',
) }}

with src_samples as (
    select *
    from {{ ref('src_samples') }}
    {% if is_incremental() %}
        where ingest_date >= (
            select max(ingest_date) from {{ this }}
        )
    {% endif %}
)

select
    *,
    cast(current_timestamp as timestamp) as dbt_updated_at
from src_samples