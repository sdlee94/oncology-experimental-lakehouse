import random
import uuid
from datetime import datetime, timedelta

from faker import Faker

import helpers
from constants import PROTOCOLS

fake = Faker()

def random_status(signed_at, witnessed_at) -> str:
    if witnessed_at:
        return "Witnessed"
    if signed_at:
        return "Signed"
    return random.choice(["Draft", "In Review"])


def random_experiment_name() -> str:
    return f"{fake.word().capitalize()} {random.choice(['Study','Experiment','Run','Assay','Screen'])}"


def random_protocol(
    antibody_relevant_only: bool = False,
) -> dict[str, str]:

    protocols = PROTOCOLS

    if antibody_relevant_only:
        protocols = [
            protocol
            for protocol in protocols
            if protocol["is_antibody_relevant"]
        ]

    selected_protocol = random.choice(protocols)

    return {
        "protocol_name": selected_protocol["protocol_name"],
        "protocol_code": selected_protocol["protocol_code"],
        "protocol_version": selected_protocol["protocol_version"],
    }


def generate_experiments(
    created_start: datetime,
    created_end: datetime,
    signed_probability: float,
    signed_max_delay_days: int,
    witnessed_probability: float,
    witnessed_max_delay_days: int,
    antibody_relevant_only: bool = False,
) -> dict:

    project = random.choice(["ONC001", "ONC002", "ONC003"])
    created_at = helpers.random_datetime_between(created_start, created_end)
    experiment_name = f"{created_at.date()} {project} Experiment"
    author_name = fake.name()

    run_date_delay = timedelta(days=random.randint(0, signed_max_delay_days))

    protocol = random_protocol(
        antibody_relevant_only=antibody_relevant_only
    )

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
            "id": f"EXP-{uuid.uuid4().hex[:8]}",
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
            "created_at": helpers.athena_timestamp_or_none(created_at),
            "signed_at": helpers.athena_timestamp_or_none(signed_at),
            "witnessed_at": helpers.athena_timestamp_or_none(witnessed_at)
        }
    }

    return record