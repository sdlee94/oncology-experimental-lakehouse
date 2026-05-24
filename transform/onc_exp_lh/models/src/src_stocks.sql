WITH raw_stocks AS (
    SELECT * FROM {{ source('onc_exp_lh', 'raw_stocks') }}
),
deduplicated as (
    select *
    from (
        select
            *,
            row_number() over (
                partition by id
                order by cast(ingest_date as date) desc, cast(updated_at as timestamp) desc
            ) as row_num
        from raw_stocks
    )
    where row_num = 1
),

typed as (
    select
        id as stock_id,
        sample_id,
        stock_owner,
        lot_number,
        quantity,
        quantity_unit,
        concentration,
        concentration_unit,
        storage_location,
        cast(created_at as timestamp) as created_at,
        cast(nullif(stored_at, '') as timestamp) as stored_at,
        cast(nullif(expiry_date, '') as date) as expiry_date,
        cast(nullif(updated_at, '') as timestamp) as updated_at,
        cast(ingest_date as date) as ingest_date
    from deduplicated
)

select
    stock_id,
    sample_id,
    stock_owner,
    lot_number,
    quantity,
    quantity_unit,
    concentration,
    concentration_unit,
    storage_location,
    created_at,
    stored_at,
    expiry_date,
    updated_at,
    case
        when expiry_date < current_date then true
        else false
    end as is_expired,
    case
        when quantity <= 0 then true
        else false
    end as is_depleted,
    date_diff('day', current_date, expiry_date) as days_until_expiry,
    ingest_date
from typed