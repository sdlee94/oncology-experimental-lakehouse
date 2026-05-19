WITH raw_samples AS (
    SELECT * FROM {{ source('onc_exp_lh', 'raw_samples') }}
)
SELECT
    id as sample_id,
    name as sample_name,
    internal_code,
    sample_type,
    created_by,
    CAST(created_at AS TIMESTAMP) AS created_at,
    CAST(updated_at AS TIMESTAMP) AS updated_at,
    CAST(run_date AS DATE) AS run_date,
    cell_line_name,
    tissue_origin,
    passage_number,
    record_hash,
    CAST(ingest_date AS DATE) AS ingest_date
FROM
    raw_samples