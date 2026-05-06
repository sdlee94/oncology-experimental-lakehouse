WITH raw_experiments AS (
    SELECT * FROM {{ source('onc_exp_lh', 'experiments') }}
)
SELECT
    experiment_id,
    experiment_name,
    project,
    status as experiment_status,
    CAST(run_date AS DATE) AS run_date,
    author as experiment_author,
    protocol_name,
    protocol_code,
    protocol_version,
    CAST(created_at AS TIMESTAMP) AS created_at,
    CAST(signed_at AS TIMESTAMP) AS signed_at,
    witnessed_by,
    CAST(witnessed_at AS TIMESTAMP) AS witnessed_at,
    {# record_hash, #}
    CAST(ingest_date AS DATE) AS ingest_date
FROM
    raw_experiments