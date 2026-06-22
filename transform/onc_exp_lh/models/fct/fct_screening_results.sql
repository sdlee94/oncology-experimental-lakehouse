{{ config(
    materialized='incremental',
    table_type='iceberg',
    unique_key='measurement_id',
    incremental_strategy='merge'
) }}

with stg_screening_results as (
    select *
    from {{ ref('stg_screening_results') }}

    {% if is_incremental() %}
        where ingest_date >= (
            select max(ingest_date)
            from {{ this }}
        )
    {% endif %}
),

final as (
    select
        result_id,
        measurement_id,
        experiment_id,
        sample_id,
        stock_id,

        protocol_code,
        protocol_name,
        protocol_version,

        antibody_clone_id,
        antibody_target_antigen,
        antibody_format,
        antibody_humanized,

        assay_name,
        assay_category,

        endpoint_name,
        endpoint_unit,
        endpoint_value,

        treatment_concentration,
        treatment_concentration_unit,
        measurement_timepoint_hours,
        control_type,

        replicate_number,
        replicates_expected,

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

    from stg_screening_results
)

select *
from final