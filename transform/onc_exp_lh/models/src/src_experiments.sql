with raw_experiments as (
    select * from {{ source('onc_exp_lh', 'raw_experiments') }}
),

deduplicated as (
    {{ deduplicate('raw_experiments', 'id', 'cast(ingest_date as date) desc') }}
),

typed as (
    select
        id as experiment_id,
        trim(name) as experiment_name,
        project,
        status as experiment_status,
        cast(run_date as date) as run_date,
        author as experiment_author,
        protocol_name,
        protocol_code,
        protocol_version,
        cast(created_at as timestamp) as created_at,
        cast(nullif(signed_at, '') as timestamp) as signed_at,
        witnessed_by,
        cast(nullif(witnessed_at, '') as timestamp) as witnessed_at,
        cast(ingest_date as date) as ingest_date
    from deduplicated
)

select * from typed