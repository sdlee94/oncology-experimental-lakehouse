import helpers

from orchestration import (
    build_generation_plan,
    generate_base_experiments,
    generate_inventory_samples,
    generate_stocks_for_samples,
    group_stock_sample_pairs_by_sample_type,
    generate_screening_results,
)

from output import (
    serialize_outputs,
    write_outputs_locally,
    write_outputs_to_s3,
)


def main() -> None:
    config = helpers.load_config()

    generation_plan = build_generation_plan(config)

    created_start = generation_plan["created_start"]
    created_end = generation_plan["created_end"]

    generation_config = generation_plan["generation_config"]
    generation_counts = generation_plan["generation_counts"]

    sample_type_distribution = generation_plan["sample_type_distribution"]

    exp_data = generate_base_experiments(
        created_start=created_start,
        created_end=created_end,
        generation_config=generation_config,
        experiment_count=generation_counts["experiments"],
    )

    sample_data = generate_inventory_samples(
        created_start=created_start,
        created_end=created_end,
        sample_count=generation_counts["samples"],
        sample_type_distribution=sample_type_distribution,
    )

    stock_data = generate_stocks_for_samples(
        samples=sample_data,
        created_start=created_start,
        created_end=created_end,
        stock_count=generation_counts["stocks"],
    )

    stocks_by_sample_type = group_stock_sample_pairs_by_sample_type(
        stocks=stock_data,
        samples=sample_data,
    )

    screening_result_data, screening_experiments = generate_screening_results(
        created_start=created_start,
        created_end=created_end,
        generation_config=generation_config,
        stocks_by_sample_type=stocks_by_sample_type,
        screening_experiment_count=generation_counts["screening_experiments"],
    )

    exp_data.extend(screening_experiments)

    contents = serialize_outputs(
        exp_data=exp_data,
        sample_data=sample_data,
        stock_data=stock_data,
        screening_result_data=screening_result_data,
    )

    if generation_plan["local"]:
        write_outputs_locally(contents)

        print("Successfully wrote synthetic data locally.")

        print(f"Experiments: {len(exp_data)}")
        print(f"Samples: {len(sample_data)}")
        print(f"Stocks: {len(stock_data)}")
        print(f"Screening Results: {len(screening_result_data)}")

    else:
        write_outputs_to_s3(
            contents=contents,
            s3_bucket=config["s3_bucket"],
        )

        print("Successfully wrote synthetic data to S3.")

        print(f"Experiments: {len(exp_data)}")
        print(f"Samples: {len(sample_data)}")
        print(f"Stocks: {len(stock_data)}")
        print(f"Screening Results: {len(screening_result_data)}")


if __name__ == "__main__":
    main()