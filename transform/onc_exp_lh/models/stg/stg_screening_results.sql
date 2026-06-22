with raw_screening_results as (
    select * from {{ source('onc_exp_lh', 'raw_screening_results') }}
),

deduplicated as (
    {{ deduplicate('raw_screening_results', 'result_id', 'cast(ingest_date as date) desc') }}
),

typed as (
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
        assay_category,
        assay_name,
        endpoint_name,
        endpoint_unit,
        cast(endpoint_value as double) as endpoint_value,
        cast(treatment_concentration as double) as treatment_concentration,
        treatment_concentration_unit,
        control_type,
        cast(replicate_number as integer) as replicate_number,
        cast(replicates_expected as integer) as replicates_expected,
        cast(measurement_timepoint_hours as double) as measurement_timepoint_hours,
        instrument_name,
        qc_flag,
        cast(ingest_date as date) as ingest_date
    from deduplicated
)

select *
from typed