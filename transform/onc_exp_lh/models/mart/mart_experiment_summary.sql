{{ config(
    materialized='table',
    table_type='iceberg',
    external_location='s3://oncology-experimental-lakehouse/mart/mart_experiment_summary/',
) }}

with experiments as (
    select *
    from {{ ref('dim_experiments') }}
),

screening_results as (
    select *
    from {{ ref('fct_screening_results') }}
),

final as (
    select
        e.experiment_id,
        e.experiment_name,
        e.project,
        e.experiment_status,
        e.run_date,
        date_trunc('month', e.run_date) as run_month,

        e.experiment_author,
        e.protocol_name,
        e.protocol_code,
        e.protocol_version,

        e.created_at,
        e.signed_at,
        e.witnessed_at,
        e.is_signed,
        e.is_witnessed,
        e.days_created_to_signed,
        e.days_signed_to_witnessed,

        case
            when e.is_signed and e.is_witnessed then 'Complete'
            when e.is_signed and not e.is_witnessed then 'Signed Not Witnessed'
            when not e.is_signed then 'Unsigned'
            else 'Other'
        end as compliance_status,

        case
            when e.is_signed
                 and e.is_witnessed
                 and coalesce(e.days_created_to_signed, 0) <= 7
                 and coalesce(e.days_signed_to_witnessed, 0) <= 7
                then true
            else false
        end as is_compliance_complete_within_7_days,

        case
            when r.experiment_id is not null then true
            else false
        end as has_screening_result,

        r.result_id,
        r.sample_id,
        r.stock_id,
        r.assay_name,
        r.endpoint_name,
        r.instrument_name,
        r.is_qc_pass,

        case
            when r.is_qc_pass then 'QC Pass'
            when r.is_qc_pass = false then 'QC Fail'
            else 'No Result'
        end as qc_status,

        r.ingest_date as screening_result_ingest_date,
        e.ingest_date as experiment_ingest_date,

        cast(current_timestamp as timestamp) as dbt_updated_at

    from experiments e
    left join screening_results r
        on e.experiment_id = r.experiment_id
)

select *
from final