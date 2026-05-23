{{ config(
    materialized='view'
) }}

with src as (
    select *
    from {{ ref('src_experiments') }}
),

deduplicated as (

    select *
    from (
        select
            *,
            row_number() over (
                partition by experiment_id
                order by ingest_date desc
            ) as row_num
        from src
    )
    where row_num = 1

)

select
    experiment_id,
    trim(upper(experiment_name)) as experiment_name,
    project,
    experiment_status,
    run_date,
    experiment_author,
    witnessed_by,
    protocol_name as protocol_name,
    protocol_code,
    protocol_version,
    created_at,
    signed_at,
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

from deduplicated