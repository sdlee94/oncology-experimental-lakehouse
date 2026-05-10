import json
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any
from faker import Faker

import helpers

fake = Faker()

# -----------------------------
# Field generators
# -----------------------------
def random_status(signed_at, witnessed_at) -> str:
    if witnessed_at:
        return "Witnessed"
    if signed_at:
        return "Signed"
    return random.choice(["Draft", "In Review"])


def random_experiment_name() -> str:
    return f"{fake.word().capitalize()} {random.choice(['Study','Experiment','Run','Assay','Screen'])}"


def random_protocol() -> dict:
    protocols = [
        ("Immune Receptor Flow Cytometry Assay", "ICI-1001", "v2.1"),
        ("T Cell Activation Co-Culture Assay", "ICI-1002", "v3.0"),
        ("Cytokine Release ELISA Assay", "ICI-1003", "v2.4"),
        ("Multiplex Cytokine Panel Assay", "ICI-1004", "v1.8"),
        ("Immune Cell Cytotoxicity Assay", "ICI-1005", "v2.2"),
        ("Checkpoint Reporter Gene Assay", "ICI-1006", "v2.7"),
        ("Serum Stability Study", "ICI-1007", "v1.9"),
        ("Pharmacokinetic Bioanalysis Assay", "ICI-1008", "v2.5"),
        ("Anti Drug Antibody Screen", "ICI-1009", "v2.0"),
        ("Dose Escalation Toxicology Study", "ICI-1010", "v3.1")
    ]
    name, code, version = random.choice(protocols)
    return {
        "name": name,
        "code": code,
        "version": version
    }

def random_sample_name() -> str:
    return f"{fake.word().capitalize()} {random.choice(['Sample', 'Specimen', 'Cell Line', 'Extract'])}"


def random_stock_name(sample_name: str) -> str:
    return f"{sample_name} Stock"


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
        "tissue_origin": cell_line_dict[cell_line_name]["tissue_origin"],
        "passage_number": random.randint(1, 50),
    }

def sample_custom_fields(sample_type: str) -> dict[str, Any]:
    if sample_type == "cell_line":
        return random_cell_line()
    return {}


def random_storage_location() -> str:
    locations = [
        "Freezer A1 Shelf 3",
        "Freezer B2 Rack 4",
        "Cold Room Shelf 1",
        "LN2 Dewar 1",
        "Refrigerator 2 Drawer 1",
        "Ambient Cabinet 5",
    ]
    return random.choice(locations)


def random_quantity() -> float:
    return round(random.uniform(0.5, 100.0), 2)


def random_quantity_unit() -> str:
    return random.choice(["mL", "uL", "g", "mg", "units"])


def random_concentration() -> float:
    return round(random.uniform(0.01, 50.0), 3)


def random_concentration_unit() -> str:
    return random.choice(["mg/mL", "ug/uL", "nM", "uM", "%"])

# -----------------------------
# Core generators
# -----------------------------
def generate_experiments(
    created_start: datetime,
    created_end: datetime,
    signed_probability: float,
    signed_max_delay_days: int,
    witnessed_probability: float,
    witnessed_max_delay_days: int,
) -> dict:

    project = random.choice(["ONC001", "ONC002", "ONC003"])
    created_at = helpers.random_datetime_between(created_start, created_end)
    experiment_name = f"{str(created_at.date)} {project} Experiment"
    author_name = fake.name()

    run_date_delay = timedelta(days=random.randint(0, signed_max_delay_days))
    protocol = random_protocol()

    signed_at = helpers.maybe_datetime_after(
        created_at,
        signed_probability,
        signed_max_delay_days
    )

    witnessed_at = None
    witnessed_by = None

    if signed_at:
        witnessed_at = helpers.maybe_datetime_after(
            signed_at,
            witnessed_probability,
            witnessed_max_delay_days
        )

        if witnessed_at:
            witnessed_by = fake.name()

    record = {
        "experiment": {
            "id": str(uuid.uuid4()),
            "project": project,
            "name": experiment_name,
            "status": random_status(signed_at, witnessed_at),
            "run_date": (created_at.date() + run_date_delay).isoformat()
        },

        "people": {
            "author": author_name,
            "witnessed_by": witnessed_by
        },

        "protocol": protocol,

        "timestamps": {
            "created_at": helpers.iso_or_none(created_at),
            "signed_at": helpers.iso_or_none(signed_at),
            "witnessed_at": helpers.iso_or_none(witnessed_at)
        }
    }

    return record

def generate_sample(created_start: datetime, created_end: datetime) -> dict[str, Any]:
    sample_type = random_sample_type()
    created_at = helpers.random_datetime_between(created_start, created_end)
    updated_at = created_at + timedelta(days=random.randint(0, 30))

    sample = {
        "common": {
            "sample_id": f"SMP-{uuid.uuid4().hex[:8]}",
            "sample_name": random_sample_name(),
            "internal_code": f"INT-{fake.random_int(1000, 9999)}",
            "sample_type": sample_type,
            "created_by": fake.name(),
            "created_at": helpers.isoformat(created_at),
            "updated_at": helpers.isoformat(updated_at),
        }
    }

    custom_fields = sample_custom_fields(sample_type)
    if custom_fields:
        sample[sample_type] = custom_fields

    return sample


def generate_stock(sample_id: str, created_start: datetime, created_end: datetime) -> dict[str, Any]:
    created_at = helpers.random_datetime_between(created_start, created_end)
    stored_at = created_at + timedelta(days=random.randint(0, 7))
    expiry_date = stored_at + timedelta(days=random.randint(30, 180))
    updated_at = stored_at + timedelta(days=random.randint(0, 30))

    return {
        "stock_id": f"STK-{uuid.uuid4().hex[:8]}",
        "sample_id": sample_id,
        "stock_owner": fake.name(),
        "lot_number": f"LOT-{fake.random_int(1000, 9999)}",
        "quantity": random_quantity(),
        "quantity_unit": random_quantity_unit(),
        "concentration": random_concentration(),
        "concentration_unit": random_concentration_unit(),
        "storage_location": random_storage_location(),
        "created_at": helpers.isoformat(created_at),
        "stored_at": helpers.isoformat(stored_at),
        "expiry_date": expiry_date.date().isoformat(),
        "updated_at": helpers.isoformat(updated_at),
    }


# -----------------------------
# Main function
# -----------------------------
def main():
    config = helpers.load_config()
    
    created_start = datetime.combine(config["created_start"], datetime.min.time())
    created_end = datetime.combine(config["created_end"], datetime.max.time().replace(hour=23, minute=59, second=59))

    exp_config = config["experiments"]

    exp_data = [
        generate_experiments(
            created_start,
            created_end,
            exp_config["signed_probability"],
            exp_config["signed_max_delay_days"],
            exp_config["witnessed_probability"],
            exp_config["witnessed_max_delay_days"],
        )
        for _ in range(exp_config["rows"])
    ]

    inv_config = config["inventory"]

    samples = [generate_sample(created_start, created_end) for _ in range(inv_config["rows_samples"])]

    stocks = [
        generate_stock(
            sample_id=random.choice(samples)["common"]["sample_id"],
            created_start=created_start,
            created_end=created_end,
        )
        for _ in range(inv_config["rows_stocks"])
    ]

    inv_data = {
        "samples": samples,
        "stocks": stocks,
    }

    
    exp_content = json.dumps(exp_data, indent=2, ensure_ascii=False)
    inv_content = json.dumps(inv_data, indent=2, ensure_ascii=False)

    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H-%M-%S")

    if config["local"]:
        Path("experiments.json").parent.mkdir(parents=True, exist_ok=True)
        with open("experiments.json", "w", encoding="utf-8") as f:
            f.write(exp_content)
        with open("inventory.json", "w", encoding="utf-8") as f:
            f.write(inv_content)
    else:
        s3_bucket = config["s3_bucket"]
        exp_s3_key = f"ingest/experiments/run_date={current_date}/{current_time}.json"
        inv_s3_key = f"ingest/inventory/run_date={current_date}/{current_time}.json"
        helpers.write_to_s3(exp_content, s3_bucket=s3_bucket, s3_key=exp_s3_key)
        helpers.write_to_s3(inv_content, s3_bucket=s3_bucket, s3_key=inv_s3_key)
        print(f"Wrote {len(exp_data)} records to {s3_bucket}/{exp_s3_key}")
        print(f"Wrote {len(inv_data)} records to {s3_bucket}/{inv_s3_key}")


if __name__ == "__main__":
    main()