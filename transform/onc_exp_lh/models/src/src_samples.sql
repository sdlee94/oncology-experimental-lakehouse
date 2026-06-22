with raw_samples as (
    select * from {{ source('onc_exp_lh', 'raw_samples') }}
),

deduplicated as (
    {{ deduplicate(
        'raw_samples',
        'id',
        "cast(ingest_date as date) desc, cast(nullif(updated_at, '') as timestamp) desc"
    ) }}
)

select
    id as sample_id,
    trim(sample_name) as sample_name,
    internal_code,
    sample_type,
    created_by,
    cast(created_at as timestamp) as created_at,
    cast(nullif(updated_at, '') as timestamp) as updated_at,
    cell_line_name,
    cell_line_tissue_origin,
    cast(cell_line_passage_number as int) as cell_line_passage_number,
    plasma_fraction_type,
    cast(plasma_donor_pool_size as int) as plasma_donor_pool_size,
    plasma_pathogen_screening_status,
    plasma_storage_temperature_c,
    protein_source_material,
    protein_lysis_buffer,
    cast(protein_yield_mg as double) as protein_yield_mg,
    cast(protein_purity_percent as double) as protein_purity_percent,
    tumor_type,
    tumor_stage,
    tumor_collection_site,
    cast(tumor_necrosis_percent as double) as tumor_necrosis_percent,
    pbmc_donor_id,
    cast(pbmc_viability_percent as double) as pbmc_viability_percent,
    pbmc_isolation_method,
    cast(pbmc_cryopreserved as boolean) as pbmc_cryopreserved,
    antibody_format,
    antibody_target_antigen,
    antibody_clone_id,
    cast(antibody_binding_affinity_nm as double) as antibody_binding_affinity_nm,
    cast(antibody_humanized as boolean) as antibody_humanized,
    cast(ingest_date as date) as ingest_date
from deduplicated