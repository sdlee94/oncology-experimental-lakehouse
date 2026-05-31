{{ config(
    materialized='table',
    table_type='iceberg',
    s3_data_dir='s3://oncology-experimental-lakehouse/mart/',
) }}

with antibody_candidates as (
    select *
    from {{ ref('dim_antibody_candidates') }}
),

screening_results as (
    select *
    from {{ ref('fct_screening_results') }}
),

joined as (
    select
        c.sample_id,
        c.sample_name,
        c.internal_code,
        c.antibody_clone_id,
        c.antibody_target_antigen,
        c.antibody_format,
        c.antibody_humanized,

        count(distinct c.stock_id) as num_available_stocks,
        count(distinct case when not c.is_expired and not c.is_depleted then c.stock_id end) as num_usable_stocks,

        count(distinct r.experiment_id) as num_experiments,
        count(distinct r.stock_id) as num_stocks_tested,
        count(r.result_id) as num_screening_results,

        avg(case
            when r.endpoint_name = 'Binding Affinity'
                then r.endpoint_value
        end) as avg_binding_affinity_nm,

        avg(case
            when r.endpoint_name = 'Cytotoxicity'
                then r.endpoint_value
        end) as avg_cytotoxicity_percent,

        avg(case
            when r.endpoint_name in ('IFN-gamma', 'IL-2')
                then r.endpoint_value
        end) as avg_cytokine_release_pg_ml,

        avg(case
            when r.endpoint_name in ('CD69 Positive T Cells', 'Reporter Inhibition')
                then r.endpoint_value
        end) as avg_activation_or_inhibition_percent,

        cast(count_if(r.is_qc_pass) as double)
            / nullif(count(r.result_id), 0) as qc_pass_rate,

        max(r.ingest_date) as latest_screening_ingest_date,
        max(c.ingest_date) as latest_candidate_ingest_date

    from antibody_candidates c
    left join screening_results r
        on c.sample_id = r.sample_id
       and c.stock_id = r.stock_id

    group by
        c.sample_id,
        c.sample_name,
        c.internal_code,
        c.antibody_clone_id,
        c.antibody_target_antigen,
        c.antibody_format,
        c.antibody_humanized
)

select
    sample_id,
    sample_name,
    internal_code,
    antibody_clone_id,
    antibody_target_antigen,
    antibody_format,
    antibody_humanized,
    num_available_stocks,
    num_usable_stocks,
    num_experiments,
    num_stocks_tested,
    num_screening_results,
    avg_binding_affinity_nm,
    avg_cytotoxicity_percent,
    avg_cytokine_release_pg_ml,
    avg_activation_or_inhibition_percent,
    qc_pass_rate,
    latest_screening_ingest_date,
    latest_candidate_ingest_date,

    case
        when avg_binding_affinity_nm <= 50
         and coalesce(avg_cytotoxicity_percent, 0) >= 50
         and coalesce(qc_pass_rate, 0) >= 0.9
            then 'Advance'
        when coalesce(qc_pass_rate, 0) < 0.8
            then 'Review QC'
        else 'Hold'
    end as candidate_recommendation,

    cast(current_timestamp as timestamp) as dbt_updated_at

from joined