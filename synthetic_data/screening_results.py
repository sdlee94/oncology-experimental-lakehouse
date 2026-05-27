import random
import uuid
from typing import Any

from constants import ANTIBODY_SCREENING_ASSAYS


def validate_ab_screening_inputs(
    experiment: dict[str, Any],
    antibody_stock_sample_pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    protocol_code = experiment["protocol"]["protocol_code"]

    if protocol_code not in ANTIBODY_SCREENING_ASSAYS:
        raise ValueError(f"Protocol code {protocol_code} is not antibody-screening relevant.")

    for antibody_stock, antibody_sample in antibody_stock_sample_pairs:
        sample_common = antibody_sample["common"]

        if sample_common["sample_type"] != "antibody_candidate":
            raise ValueError(f"Sample {sample_common['id']} is not an antibody candidate.")

        if antibody_stock["sample_id"] != sample_common["id"]:
            raise ValueError("Selected stock does not belong to selected antibody candidate sample.")

    return ANTIBODY_SCREENING_ASSAYS[protocol_code]


def build_supporting_materials(
    supporting_stock_sample_pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> list[dict[str, Any]]:
    return [
        {
            "sample_id": sample["common"]["id"],
            "stock_id": stock["id"],
            "sample_type": sample["common"]["sample_type"],
        }
        for stock, sample in supporting_stock_sample_pairs
    ]


def generate_measurements(assay: dict[str, Any]) -> list[dict[str, Any]]:
    measurements = []

    for endpoint_name in assay["endpoint_names"]:
        for concentration in assay["treatment_concentrations"]:
            for timepoint in assay["measurement_timepoints_hours"]:
                measurement_id = f"MEA-{uuid.uuid4().hex[:10]}"

                for replicate_number in range(1, assay["replicates_per_measurement"] + 1):
                    measurements.append(
                        {
                            "measurement_id": measurement_id,
                            "endpoint_name": endpoint_name,
                            "concentration": concentration,
                            "timepoint": timepoint,
                            "replicate_number": replicate_number,
                        }
                    )

    return measurements


def build_ab_screening_row(
    *,
    result_id: str,
    measurement_id: str,
    experiment: dict[str, Any],
    antibody_stock: dict[str, Any],
    antibody_sample: dict[str, Any],
    supporting_materials: list[dict[str, Any]],
    assay: dict[str, Any],
    endpoint_name: str,
    concentration: float,
    timepoint: int,
    replicate_number: int,
    instrument_name: str,
    qc_flag: str,
) -> dict[str, Any]:
    protocol = experiment["protocol"]
    antibody_common = antibody_sample["common"]
    antibody_candidate = antibody_sample["antibody_candidate"]

    min_value, max_value = assay["value_range"]

    return {
        "result_id": result_id,
        "measurement_id": measurement_id,
        "experiment_id": experiment["experiment"]["id"],

        "stock_id": antibody_stock["id"],
        "sample_id": antibody_common["id"],

        "supporting_materials": supporting_materials,

        "protocol_code": protocol["protocol_code"],
        "protocol_name": protocol["protocol_name"],
        "protocol_version": protocol["protocol_version"],

        "antibody_clone_id": antibody_candidate["antibody_clone_id"],
        "antibody_target_antigen": antibody_candidate["antibody_target_antigen"],
        "antibody_format": antibody_candidate["antibody_format"],
        "antibody_humanized": antibody_candidate["antibody_humanized"],

        "assay_category": assay["assay_category"],
        "assay_name": assay["assay_name"],

        "endpoint_name": endpoint_name,
        "endpoint_unit": assay["endpoint_unit"],
        "endpoint_value": round(random.uniform(min_value, max_value), 3),

        "treatment_concentration": concentration,
        "treatment_concentration_unit": "nM",
        "control_type": "Test Article",

        "replicate_number": replicate_number,
        "replicates_expected": assay["replicates_per_measurement"],
        "measurement_timepoint_hours": timepoint,

        "instrument_name": instrument_name,
        "qc_flag": qc_flag,
    }


def generate_ab_screening_result_rows(
    experiment: dict[str, Any],
    antibody_stock_sample_pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    supporting_stock_sample_pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> list[dict[str, Any]]:
    assay = validate_ab_screening_inputs(
        experiment,
        antibody_stock_sample_pairs,
    )

    result_id = f"RES-{uuid.uuid4().hex[:10]}"
    instrument_name = random.choice(assay["instrument_names"])
    qc_flag = "Pass" if random.random() >= 0.05 else "Fail"

    supporting_materials = build_supporting_materials(
        supporting_stock_sample_pairs,
    )

    measurements = generate_measurements(assay)

    rows = []

    for antibody_stock, antibody_sample in antibody_stock_sample_pairs:
        for measurement in measurements:
            rows.append(
                build_ab_screening_row(
                    result_id=result_id,
                    measurement_id=measurement["measurement_id"],
                    experiment=experiment,
                    antibody_stock=antibody_stock,
                    antibody_sample=antibody_sample,
                    supporting_materials=supporting_materials,
                    assay=assay,
                    endpoint_name=measurement["endpoint_name"],
                    concentration=measurement["concentration"],
                    timepoint=measurement["timepoint"],
                    replicate_number=measurement["replicate_number"],
                    instrument_name=instrument_name,
                    qc_flag=qc_flag,
                )
            )

    return rows