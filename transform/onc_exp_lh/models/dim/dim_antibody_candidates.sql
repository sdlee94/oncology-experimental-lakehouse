{{ config(
    materialized='table',
    table_type='iceberg'
) }}

with antibody_samples as (
    select
        sample_id,
        sample_name,
        internal_code,
        sample_type,
        created_by,
        created_at,
        updated_at,
        antibody_clone_id,
        antibody_target_antigen,
        antibody_format,
        antibody_binding_affinity_nm,
        antibody_humanized,
        ingest_date
    from {{ ref('dim_samples') }}
    where sample_type = 'antibody_candidate'
),

antibody_stocks as (
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
        created_at as stock_created_at,
        stored_at,
        expiry_date,
        updated_at as stock_updated_at,
        is_expired,
        is_depleted,
        days_until_expiry,
        ingest_date as stock_ingest_date
    from {{ ref('dim_stocks') }}
)

select
    s.sample_id,
    s.sample_name,
    s.internal_code,
    s.sample_type,
    s.created_by,
    s.created_at,
    s.updated_at,

    s.antibody_clone_id,
    s.antibody_target_antigen,
    s.antibody_format,
    s.antibody_binding_affinity_nm,
    s.antibody_humanized,

    st.stock_id,
    st.stock_owner,
    st.lot_number,
    st.quantity,
    st.quantity_unit,
    st.concentration,
    st.concentration_unit,
    st.storage_location,
    st.stock_created_at,
    st.stored_at,
    st.expiry_date,
    st.stock_updated_at,
    st.is_expired,
    st.is_depleted,
    st.days_until_expiry,

    greatest(s.ingest_date, st.stock_ingest_date) as ingest_date,
    cast(current_timestamp as timestamp) as dbt_updated_at

from antibody_samples s
left join antibody_stocks st
    on s.sample_id = st.sample_id