import json
from numpy import rint
import yaml
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta

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

# -----------------------------
# Core generator
# -----------------------------
def generate_record(
    created_start: datetime,
    created_end: datetime,
    signed_probability: float,
    signed_max_delay_days: int,
    witnessed_probability: float,
    witnessed_max_delay_days: int,
) -> dict:

    project = random.choice(["ONC001", "ONC002", "ONC003"])
    created_at = helpers.random_datetime_between(created_start, created_end)
    experiment_name = f"{str(created_at)} {project} Experiment"
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

# -----------------------------
# Main function
# -----------------------------
def main():
    config = helpers.load_config()
    config = config["synthetic_data"]["experiments"]
    
    created_start = datetime.combine(config["created_start"], datetime.min.time())
    created_end = datetime.combine(config["created_end"], datetime.max.time().replace(hour=23, minute=59, second=59))

    rows = [
        generate_record(
            created_start,
            created_end,
            config["signed_probability"],
            config["signed_max_delay_days"],
            config["witnessed_probability"],
            config["witnessed_max_delay_days"],
        )
        for _ in range(config["rows"])
    ]

    content = json.dumps(rows, indent=2, ensure_ascii=False)
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H-%M-%S")

    if config["local"]:
        Path("experiments.json").parent.mkdir(parents=True, exist_ok=True)
        with open("experiments.json", "w", encoding="utf-8") as f:
            f.write(content)
    else:
        s3_bucket = config["s3_bucket"]
        s3_key = f"ingest/experiments/run_date={current_date}/{current_time}.json"
        helpers.write_to_s3(content, s3_bucket=s3_bucket, s3_key=s3_key)
        print(f"Wrote {len(rows)} records to {s3_bucket}/{s3_key}")


if __name__ == "__main__":
    main()