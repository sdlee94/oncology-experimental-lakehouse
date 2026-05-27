import math
import random
from datetime import datetime
from typing import Any

from constants import ANTIBODY_SCREENING_ASSAYS
from experiments import generate_experiments
from samples import generate_sample
from screening_results import generate_ab_screening_result_rows
from stocks import generate_stock


StockSamplePair = tuple[dict[str, Any], dict[str, Any]]


def get_generation_window(config: dict[str, Any]) -> tuple[datetime, datetime]:
    created_start = datetime.combine(config["created_start"], datetime.min.time())
    created_end = datetime.combine(config["created_end"], datetime.max.time())
    return created_start, created_end


def calculate_duration_months(
    created_start: datetime,
    created_end: datetime,
) -> float:
    duration_days = max((created_end - created_start).days + 1, 1)
    return duration_days / 30.44


def calculate_generation_counts(
    created_start: datetime,
    created_end: datetime,
    generation_config: dict[str, Any],
) -> dict[str, int]:
    duration_months = calculate_duration_months(created_start, created_end)

    experiment_count = max(
        1,
        round(duration_months * generation_config["experiments_per_month"]),
    )

    sample_count = max(
        1,
        round(experiment_count * generation_config["samples_per_experiment"]),
    )

    stock_count = max(
        sample_count,
        round(sample_count * generation_config["stocks_per_sample"]),
    )

    screening_experiment_count = max(
        1,
        round(experiment_count * generation_config["screening_experiment_fraction"]),
    )

    return {
        "experiments": experiment_count,
        "samples": sample_count,
        "stocks": stock_count,
        "screening_experiments": screening_experiment_count,
    }


def build_generation_plan(config: dict[str, Any]) -> dict[str, Any]:
    created_start, created_end = get_generation_window(config)

    generation_config = config["generation"]

    generation_counts = calculate_generation_counts(
        created_start=created_start,
        created_end=created_end,
        generation_config=generation_config,
    )

    return {
        "local": config.get("local", True),
        "created_start": created_start,
        "created_end": created_end,
        "generation_config": generation_config,
        "generation_counts": generation_counts,
        "sample_type_distribution": config["sample_type_distribution"],
    }


def generate_base_experiments(
    created_start: datetime,
    created_end: datetime,
    generation_config: dict[str, Any],
    experiment_count: int,
) -> list[dict[str, Any]]:
    return [
        generate_experiments(
            created_start=created_start,
            created_end=created_end,
            signed_probability=generation_config["signed_probability"],
            signed_max_delay_days=generation_config["signed_max_delay_days"],
            witnessed_probability=generation_config["witnessed_probability"],
            witnessed_max_delay_days=generation_config["witnessed_max_delay_days"],
        )
        for _ in range(experiment_count)
    ]


def calculate_sample_type_counts(
    total_samples: int,
    sample_type_distribution: dict[str, float],
) -> dict[str, int]:
    counts = {
        sample_type: math.floor(total_samples * proportion)
        for sample_type, proportion in sample_type_distribution.items()
    }

    remaining = total_samples - sum(counts.values())
    sample_types = list(sample_type_distribution.keys())

    for _ in range(remaining):
        selected_type = random.choice(sample_types)
        counts[selected_type] += 1

    return counts


def generate_inventory_samples(
    created_start: datetime,
    created_end: datetime,
    sample_count: int,
    sample_type_distribution: dict[str, float],
) -> list[dict[str, Any]]:
    sample_type_counts = calculate_sample_type_counts(
        total_samples=sample_count,
        sample_type_distribution=sample_type_distribution,
    )

    samples = []

    for sample_type, count in sample_type_counts.items():
        samples.extend(
            generate_sample(
                created_start=created_start,
                created_end=created_end,
                sample_type=sample_type,
            )
            for _ in range(count)
        )

    return samples


def generate_stocks_for_samples(
    samples: list[dict[str, Any]],
    created_start: datetime,
    created_end: datetime,
    stock_count: int,
) -> list[dict[str, Any]]:
    if not samples:
        return []

    stocks = []

    for sample in samples:
        stocks.append(
            generate_stock(
                sample_id=sample["common"]["id"],
                created_start=created_start,
                created_end=created_end,
            )
        )

    remaining_stock_count = max(stock_count - len(stocks), 0)

    for _ in range(remaining_stock_count):
        sample = random.choice(samples)

        stocks.append(
            generate_stock(
                sample_id=sample["common"]["id"],
                created_start=created_start,
                created_end=created_end,
            )
        )

    return stocks


def index_samples_by_id(
    samples: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        sample["common"]["id"]: sample
        for sample in samples
    }


def group_stock_sample_pairs_by_sample_type(
    stocks: list[dict[str, Any]],
    samples: list[dict[str, Any]],
) -> dict[str, list[StockSamplePair]]:
    sample_by_id = index_samples_by_id(samples)

    grouped: dict[str, list[StockSamplePair]] = {}

    for stock in stocks:
        sample = sample_by_id[stock["sample_id"]]
        sample_type = sample["common"]["sample_type"]

        grouped.setdefault(sample_type, []).append((stock, sample))

    return grouped


def choose_supporting_pairs(
    assay: dict[str, Any],
    stocks_by_sample_type: dict[str, list[StockSamplePair]],
) -> list[StockSamplePair]:
    supporting_pairs = []

    for required_sample_type in assay["required_supporting_sample_types"]:
        available_pairs = stocks_by_sample_type.get(required_sample_type, [])

        if available_pairs:
            supporting_pairs.append(random.choice(available_pairs))

    return supporting_pairs


def choose_antibody_pairs_for_assay(
    assay: dict[str, Any],
    antibody_stock_sample_pairs: list[StockSamplePair],
) -> list[StockSamplePair]:
    min_candidates, max_candidates = assay["antibody_candidates_per_result"]

    num_candidates = min(
        len(antibody_stock_sample_pairs),
        random.randint(min_candidates, max_candidates),
    )

    return random.sample(
        antibody_stock_sample_pairs,
        num_candidates,
    )


def generate_screening_experiment(
    created_start: datetime,
    created_end: datetime,
    generation_config: dict[str, Any],
) -> dict[str, Any]:
    return generate_experiments(
        created_start=created_start,
        created_end=created_end,
        signed_probability=generation_config["signed_probability"],
        signed_max_delay_days=generation_config["signed_max_delay_days"],
        witnessed_probability=generation_config["witnessed_probability"],
        witnessed_max_delay_days=generation_config["witnessed_max_delay_days"],
        antibody_relevant_only=True,
    )


def determine_screening_run_count(
    antibody_stock_sample_pairs: list[StockSamplePair],
    requested_screening_count: int,
) -> int:
    return min(
        len(antibody_stock_sample_pairs),
        requested_screening_count,
    )


def generate_screening_results(
    created_start: datetime,
    created_end: datetime,
    generation_config: dict[str, Any],
    stocks_by_sample_type: dict[str, list[StockSamplePair]],
    screening_experiment_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    antibody_stock_sample_pairs = stocks_by_sample_type.get(
        "antibody_candidate",
        [],
    )

    num_screening_runs = determine_screening_run_count(
        antibody_stock_sample_pairs=antibody_stock_sample_pairs,
        requested_screening_count=screening_experiment_count,
    )

    screening_results = []
    screening_experiments = []

    for _ in range(num_screening_runs):
        experiment = generate_screening_experiment(
            created_start=created_start,
            created_end=created_end,
            generation_config=generation_config,
        )

        protocol_code = experiment["protocol"]["protocol_code"]
        assay = ANTIBODY_SCREENING_ASSAYS[protocol_code]

        selected_antibody_pairs = choose_antibody_pairs_for_assay(
            assay=assay,
            antibody_stock_sample_pairs=antibody_stock_sample_pairs,
        )

        supporting_pairs = choose_supporting_pairs(
            assay=assay,
            stocks_by_sample_type=stocks_by_sample_type,
        )

        rows = generate_ab_screening_result_rows(
            experiment=experiment,
            antibody_stock_sample_pairs=selected_antibody_pairs,
            supporting_stock_sample_pairs=supporting_pairs,
        )

        screening_results.extend(rows)
        screening_experiments.append(experiment)

    return screening_results, screening_experiments
