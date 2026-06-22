with raw_stocks as (
    select * from {{ source('onc_exp_lh', 'raw_stocks') }}
),

deduplicated as (
    {{ deduplicate(
        'raw_stocks',
        'id',
        "cast(ingest_date as date) desc, cast(nullif(updated_at, '') as timestamp) desc"
    ) }}
),

typed as (
    select
        id as stock_id,
        sample_id,
        stock_owner,
        lot_number,
        cast(quantity as double) as quantity,
        quantity_unit,
        cast(concentration as double) as concentration,
        concentration_unit,
        storage_location,
        cast(created_at as timestamp) as created_at,
        cast(nullif(stored_at, '') as timestamp) as stored_at,
        cast(nullif(expiry_date, '') as date) as expiry_date,
        cast(nullif(updated_at, '') as timestamp) as updated_at,
        cast(ingest_date as date) as ingest_date
    from deduplicated
)

select * from typed