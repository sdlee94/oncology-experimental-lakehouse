with stg_experiments as (
    select * from {{ ref('stg_experiments') }}
)

select
    *,
    signed_at is not null   as is_signed,
    witnessed_at is not null as is_witnessed,
    case
        when created_at is not null and signed_at is not null
            then date_diff('day', created_at, signed_at)
    end as days_created_to_signed,
    case
        when signed_at is not null and witnessed_at is not null
            then date_diff('day', signed_at, witnessed_at)
    end as days_signed_to_witnessed
from stg_experiments
