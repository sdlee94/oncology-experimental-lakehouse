import json
from datetime import datetime
from typing import Any

import helpers


def serialize_outputs(
    exp_data: list[dict[str, Any]],
    sample_data: list[dict[str, Any]],
    stock_data: list[dict[str, Any]],
    screening_result_data: list[dict[str, Any]],
) -> dict[str, str]:
    return {
        "experiments": json.dumps(exp_data, indent=2, ensure_ascii=False),
        "samples": json.dumps(sample_data, indent=2, ensure_ascii=False),
        "stocks": json.dumps(stock_data, indent=2, ensure_ascii=False),
        "screening_results": json.dumps(
            screening_result_data,
            indent=2,
            ensure_ascii=False,
        ),
    }


def write_outputs_locally(contents: dict[str, str]) -> None:
    output_paths = {
        "experiments": "data/experiments.json",
        "samples": "data/samples.json",
        "stocks": "data/stock.json",
        "screening_results": "data/screening_results.json",
    }

    for dataset_name, output_path in output_paths.items():
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(contents[dataset_name])


def build_s3_key(
    dataset_name: str,
    current_date: str,
    current_time: str,
) -> str:
    return f"ingest/{dataset_name}/run_date={current_date}/{current_time}.json"


def write_outputs_to_s3(
    contents: dict[str, str],
    s3_bucket: str,
) -> None:
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H-%M-%S")

    for dataset_name, content in contents.items():
        s3_key = build_s3_key(
            dataset_name=dataset_name,
            current_date=current_date,
            current_time=current_time,
        )

        helpers.write_to_s3(
            content,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
        )

        print(f"Wrote {dataset_name} to {s3_bucket}/{s3_key}")