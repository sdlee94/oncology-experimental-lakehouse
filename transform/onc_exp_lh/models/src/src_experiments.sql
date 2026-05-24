WITH raw_experiments AS (
    SELECT * FROM {{ source('onc_exp_lh', 'raw_experiments') }}
),

deduplicated as (
    select *
    from (
        select
            *,
            row_number() over (
                partition by id
                order by cast(ingest_date as date) desc
            ) as row_num
        from raw_experiments
    )
    where row_num = 1
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

select
    experiment_id,
    experiment_name,
    project,
    experiment_status,
    run_date,
    experiment_author,
    protocol_name,
    protocol_code,
    protocol_version,
    created_at,
    signed_at,
    witnessed_by,
    witnessed_at,
    case
        when signed_at is not null then true
        else false
    end as is_signed,
    case
        when witnessed_at is not null then true
        else false
    end as is_witnessed,
    case
        when created_at is not null
         and signed_at is not null
            then date_diff('day', created_at, signed_at)
    end as days_created_to_signed,
    case
        when signed_at is not null
         and witnessed_at is not null
            then date_diff('day', signed_at, witnessed_at)
    end as days_signed_to_witnessed,
    ingest_date
from typed