WITH raw_experiments AS (
    SELECT * FROM {{ source('onc_exp_lh', 'experiments') }}
)
SELECT
    *
FROM
    raw_experiments