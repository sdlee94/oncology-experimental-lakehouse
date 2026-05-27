import random
import uuid
from datetime import datetime, timedelta
from typing import Any
from faker import Faker

import helpers

fake = Faker()


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


def generate_stock(
    sample_id: str,
    created_start: datetime,
    created_end: datetime,
) -> dict[str, Any]:
    created_at = helpers.random_datetime_between(created_start, created_end)
    stored_at = created_at + timedelta(days=random.randint(0, 7))
    expiry_date = stored_at + timedelta(days=random.randint(30, 180))
    updated_at = stored_at + timedelta(days=random.randint(0, 30))

    return {
        "id": f"STK-{uuid.uuid4().hex[:8]}",
        "sample_id": sample_id,
        "stock_owner": fake.name(),
        "lot_number": f"LOT-{fake.random_int(1000, 9999)}",
        "quantity": random_quantity(),
        "quantity_unit": random_quantity_unit(),
        "concentration": random_concentration(),
        "concentration_unit": random_concentration_unit(),
        "storage_location": random_storage_location(),
        "created_at": helpers.athena_timestamp_or_none(created_at),
        "stored_at": helpers.athena_timestamp_or_none(stored_at),
        "expiry_date": expiry_date.date().isoformat(),
        "updated_at": helpers.athena_timestamp_or_none(updated_at),
    }