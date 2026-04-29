from movement.io import load_pose_csv, print_data_summary
from movement.config import LANDMARKS, CONNECTIONS
from movement.utils import validate_landmark_columns
from movement.visualization import create_pose_animation


def main():
    csv_path = "data/sample/mediapipe_forward_bend_sample.csv"

    df = load_pose_csv(csv_path)
    print_data_summary(df)

    validate_landmark_columns(df, LANDMARKS)

    fig = create_pose_animation(
        df=df,
        landmarks=LANDMARKS,
        connections=CONNECTIONS,
    )

    fig.show()


if __name__ == "__main__":
    main()