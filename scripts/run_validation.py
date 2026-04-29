import json

from movement.io import load_pose_csv, print_data_summary
from movement.config import (
    make_required_columns,
    make_coordinate_columns,
    make_visibility_columns,
)
from movement.validation import run_basic_validation


def main():
    csv_path = "data/sample/mediapipe_forward_bend_sample.csv"

    df = load_pose_csv(csv_path)
    print_data_summary(df)

    report = run_basic_validation(
        df=df,
        required_columns=make_required_columns(),
        coordinate_columns=make_coordinate_columns(),
        visibility_columns=make_visibility_columns(),
    )

    print("\nValidation passed:", report["passed"])
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()