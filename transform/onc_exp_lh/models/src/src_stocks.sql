WITH raw_stocks AS (
    SELECT * FROM {{ source('onc_exp_lh', 'raw_stocks') }}
)
SELECT
    id as stock_id,
    sample_id,
    stock_owner,
    lot_number,
    quantity,
    quantity_unit,
    concentration,
    concentration_unit,
    storage_location,
    CAST(created_at AS TIMESTAMP) AS created_at,
    CAST(stored_at AS DATE) AS stored_at,
    CAST(expiry_date AS DATE) AS expiry_date,
    CAST(updated_at AS TIMESTAMP) AS updated_at,
    record_hash,
    CAST(ingest_date AS DATE) AS ingest_date
FROM
    raw_stocks