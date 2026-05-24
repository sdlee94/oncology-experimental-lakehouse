{{ config(
    materialized='incremental',
    table_type='iceberg',
    unique_key='result_id',
    incremental_strategy='merge'
) }}

with src_screening_results as (
    select *
    from {{ ref('src_screening_results') }}

    {% if is_incremental() %}
        where ingest_date >= (
            select max(ingest_date)
            from {{ this }}
        )
    {% endif %}
)

select
    result_id,
    experiment_id,
    sample_id,
    stock_id,
    protocol_code,
    assay_name,
    assay_category,
    endpoint_name,
    endpoint_unit,
    replicate_number,
    endpoint_value,
    treatment_concentration,
    treatment_concentration_unit,
    measurement_timepoint_hours,
    control_type,
    qc_flag,
    case
        when qc_flag = 'Pass' then true
        else false
    end as is_qc_pass,
    case
        when control_type != 'Test Article' then true
        else false
    end as is_control,
    instrument_name,
    ingest_date,
    cast(current_timestamp as timestamp) as dbt_updated_at
from src_screening_results