import random
import uuid
from typing import Any
from datetime import datetime, timedelta
from faker import Faker

import helpers

fake = Faker()


def random_sample_name() -> str:
    return f"{fake.word().capitalize()} {random.choice(['Sample', 'Specimen', 'Cell Line', 'Extract'])}"


def random_sample_type() -> str:
    return random.choice(
        [
            "cell_line",
            "plasma_fraction",
            "protein_extract",
            "tumor_sample",
            "pbmc",
            "antibody_candidate",
        ]
    )

def random_cell_line():
    cell_line_dict = {
        "HeLa": {"tissue_origin": "Cervical Cancer"},
        "HEK283T": {"tissue_origin": "Kidney"},
        "Jurkat": {"tissue_origin": "T-cell Leukemia"},
        "MCF7": {"tissue_origin": "Breast Cancer"},
        "A549": {"tissue_origin": "Lung Cancer"},
    }

    cell_line_name = fake.random_element(list(cell_line_dict.keys()))

    return {
        "cell_line_name": cell_line_name,
        "cell_line_tissue_origin": cell_line_dict[cell_line_name]["tissue_origin"],
        "cell_line_passage_number": random.randint(1, 50),
    }

def random_plasma_fraction():
    fractions = ["Fraction I", "Fraction II", "Fraction III", "Cryoprecipitate"]
    return {
        "plasma_fraction_type": random.choice(fractions),
        "plasma_donor_pool_size": random.randint(10, 500),
        "plasma_pathogen_screening_status": random.choice(
            ["pending", "passed", "failed"]
        ),
        "plasma_storage_temperature_c": random.choice([-80, -20, 4]),
    }


def random_protein_extract():
    sources = ["Tumor Tissue", "PBMC", "CHO Cells", "E. coli"]
    return {
        "protein_source_material": random.choice(sources),
        "protein_lysis_buffer": random.choice(
            ["RIPA", "NP-40", "Tris-HCl", "Urea Buffer"]
        ),
        "protein_yield_mg": round(random.uniform(0.1, 50.0), 2),
        "protein_purity_percent": round(random.uniform(70, 99.9), 1),
    }


def random_tumor_sample():
    tumor_types = [
        "Melanoma",
        "NSCLC",
        "Breast Cancer",
        "Colorectal Cancer",
    ]

    return {
        "tumor_type": random.choice(tumor_types),
        "tumor_stage": random.choice(["I", "II", "III", "IV"]),
        "tumor_collection_site": random.choice(
            ["Primary", "Metastatic", "Lymph Node"]
        ),
        "tumor_necrosis_percent": round(random.uniform(0, 80), 1),
    }


def random_pbmc():
    return {
        "pbmc_donor_id": f"DNR-{fake.random_int(10000, 99999)}",
        "pbmc_viability_percent": round(random.uniform(70, 99.5), 1),
        "pbmc_isolation_method": random.choice(
            ["Ficoll", "Leucosep", "Density Gradient"]
        ),
        "pbmc_cryopreserved": random.choice([True, False]),
    }

def random_antibody_candidate():
    formats = ["IgG1", "IgG4", "Bispecific", "Fab"]

    targets = [
        "PD-1",
        "PD-L1",
        "CTLA-4",
        "LAG-3",
        "TIGIT",
    ]

    return {
        "antibody_format": random.choice(formats),
        "antibody_target_antigen": random.choice(targets),
        "antibody_clone_id": f"CLN-{fake.random_int(1000, 9999)}",
        "antibody_binding_affinity_nm": round(random.uniform(0.01, 500), 3),
        "antibody_humanized": random.choice([True, False]),
    }

def sample_custom_fields(sample_type: str) -> dict[str, Any]:
    generators = {
        "cell_line": random_cell_line,
        "plasma_fraction": random_plasma_fraction,
        "protein_extract": random_protein_extract,
        "tumor_sample": random_tumor_sample,
        "pbmc": random_pbmc,
        "antibody_candidate": random_antibody_candidate,
    }

    generator = generators.get(sample_type)

    if generator:
        return generator()

    return {}


def generate_sample(
    created_start: datetime,
    created_end: datetime,
    sample_type: str | None = None,
) -> dict[str, Any]:
    sample_type = sample_type or random_sample_type()

    created_at = helpers.random_datetime_between(created_start, created_end)
    updated_at = created_at + timedelta(days=random.randint(0, 30))

    sample = {
        "common": {
            "id": f"SMP-{uuid.uuid4().hex[:8]}",
            "sample_name": random_sample_name(),
            "internal_code": f"INT-{fake.random_int(1000, 9999)}",
            "sample_type": sample_type,
            "created_by": fake.name(),
            "created_at": helpers.athena_timestamp_or_none(created_at),
            "updated_at": helpers.athena_timestamp_or_none(updated_at),
        }
    }

    custom_fields = sample_custom_fields(sample_type)

    if custom_fields:
        sample[sample_type] = custom_fields

    return sample