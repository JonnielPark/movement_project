"""
합성 데이터 생성 및 시뮬레이션 조건 부여

정상 포즈 데이터프레임에 인위적 ROM 제한 / 좌표 잡음 / 가려짐 / 속도 이상을
주입해 강건성 평가용 변형 데이터셋을 생성한다.

모든 함수는 원본 데이터프레임을 수정하지 않고 복사본을 반환한다.
simulation_log dict는 어떤 처리가 적용됐는지를 기록한다.

단위:
  노이즈 σ : torso_length_ratio
  속도 스파이크 크기 : torso_length_ratio
  ROM 제한 : degree
"""
from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────

def _xyz_cols(lm: str) -> list[str]:
    return [f"{lm}_x", f"{lm}_y", f"{lm}_z"]


def _get_torso_scale(df: pd.DataFrame) -> float:
    """시퀀스 중간값 몸통 길이 (torso_length_ratio 기준 1.0에 해당하는 raw 스케일)."""
    if "torso_length" in df.columns:
        return float(df["torso_length"].median())
    # torso_length 컬럼 없으면 hip-shoulder 거리로 추정
    try:
        lhs = df[["left_shoulder_x", "left_shoulder_y", "left_shoulder_z"]].values
        rhs = df[["right_shoulder_x", "right_shoulder_y", "right_shoulder_z"]].values
        lhh = df[["left_hip_x", "left_hip_y", "left_hip_z"]].values
        rhh = df[["right_hip_x", "right_hip_y", "right_hip_z"]].values
        sc = (lhs + rhs) / 2.0
        hc = (lhh + rhh) / 2.0
        lengths = np.linalg.norm(sc - hc, axis=1)
        return float(np.median(lengths))
    except KeyError:
        return 1.0


# ── 공개 API ─────────────────────────────────────────────────────────────────

def add_gaussian_noise(
    df: pd.DataFrame,
    sigma_torso_ratio: float,
    landmarks: list[str] | None = None,
    seed: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """모든(또는 지정) 랜드마크의 x/y/z 좌표에 가우시안 잡음을 추가한다.

    Parameters
    ----------
    df : pd.DataFrame
        원본 포즈 데이터프레임 (수정하지 않음).
    sigma_torso_ratio : float
        잡음 표준편차 (torso_length_ratio 단위).
        예: 0.01 = 몸통 길이의 1%.
    landmarks : list[str], optional
        잡음을 추가할 랜드마크 목록. None이면 x/y/z 컬럼 전체 적용.
    seed : int, optional
        재현성용 난수 시드.

    Returns
    -------
    (noisy_df, simulation_log)
    """
    rng = np.random.default_rng(seed)
    df_out = df.copy()
    scale = _get_torso_scale(df)
    sigma_raw = sigma_torso_ratio * scale

    if landmarks is None:
        coord_cols = [c for c in df.columns if c.endswith(("_x", "_y", "_z"))
                      and not c.startswith(("left_norm", "right_norm"))]
    else:
        coord_cols = [c for lm in landmarks for c in _xyz_cols(lm) if c in df.columns]

    noise = rng.normal(0.0, sigma_raw, size=(len(df_out), len(coord_cols)))
    df_out[coord_cols] += noise

    log: dict[str, Any] = {
        "simulation": "gaussian_noise",
        "sigma_torso_ratio": sigma_torso_ratio,
        "sigma_raw": round(sigma_raw, 6),
        "num_columns_affected": len(coord_cols),
        "seed": seed,
    }
    return df_out, log


def add_occlusion(
    df: pd.DataFrame,
    target_landmarks: list[str],
    frame_range: tuple[int, int],
    zero_visibility: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """지정 랜드마크를 지정 프레임 구간에서 가려진 것으로 처리한다.

    처리 방식:
      - 해당 프레임의 좌표를 NaN으로 대체 (모델이 결측으로 처리하도록).
      - visibility를 0.0으로 설정 (zero_visibility=True 시).

    Parameters
    ----------
    df : pd.DataFrame
    target_landmarks : list[str]
        가려짐을 적용할 랜드마크 이름 목록.
    frame_range : tuple[int, int]
        (start_frame, end_frame) 포함 범위.
    zero_visibility : bool
        True이면 visibility도 0으로 설정.

    Returns
    -------
    (occluded_df, simulation_log)
    """
    df_out = df.copy()
    start_f, end_f = frame_range
    mask = (df_out["frame"] >= start_f) & (df_out["frame"] <= end_f)
    num_frames = int(mask.sum())

    affected_cols: list[str] = []
    for lm in target_landmarks:
        for ax in ("x", "y", "z"):
            col = f"{lm}_{ax}"
            if col in df_out.columns:
                df_out.loc[mask, col] = np.nan
                affected_cols.append(col)
        if zero_visibility:
            vis_col = f"{lm}_visibility"
            if vis_col in df_out.columns:
                df_out.loc[mask, vis_col] = 0.0

    log: dict[str, Any] = {
        "simulation": "occlusion",
        "target_landmarks": target_landmarks,
        "frame_range": list(frame_range),
        "num_frames_affected": num_frames,
        "zero_visibility": zero_visibility,
        "affected_columns": affected_cols,
    }
    return df_out, log


def add_velocity_spike(
    df: pd.DataFrame,
    target_landmarks: list[str],
    spike_frames: list[int],
    spike_magnitude_torso_ratio: float = 0.5,
    seed: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """지정 프레임에서 지정 랜드마크의 좌표에 위치 점프를 삽입한다.

    속도 이상 감지(preprocessing velocity check)의 동작을 검증하기 위한 조건.

    Parameters
    ----------
    df : pd.DataFrame
    target_landmarks : list[str]
    spike_frames : list[int]
        점프가 삽입될 프레임 번호 목록.
    spike_magnitude_torso_ratio : float
        점프 크기 (torso_length_ratio 단위).
    seed : int, optional

    Returns
    -------
    (spiked_df, simulation_log)
    """
    rng = np.random.default_rng(seed)
    df_out = df.copy()
    scale = _get_torso_scale(df)
    magnitude_raw = spike_magnitude_torso_ratio * scale

    frame_col = "frame" if "frame" in df_out.columns else df_out.index.name

    for lm in target_landmarks:
        for spike_f in spike_frames:
            mask = df_out["frame"] == spike_f
            if not mask.any():
                continue
            direction = rng.normal(0.0, 1.0, size=3)
            direction /= np.linalg.norm(direction) + 1e-9
            for i, ax in enumerate(("x", "y", "z")):
                col = f"{lm}_{ax}"
                if col in df_out.columns:
                    df_out.loc[mask, col] += direction[i] * magnitude_raw

    log: dict[str, Any] = {
        "simulation": "velocity_spike",
        "target_landmarks": target_landmarks,
        "spike_frames": spike_frames,
        "spike_magnitude_torso_ratio": spike_magnitude_torso_ratio,
        "spike_magnitude_raw": round(magnitude_raw, 6),
        "seed": seed,
    }
    return df_out, log


def restrict_rom(
    df: pd.DataFrame,
    joint: str,
    restriction_deg: float,
    landmarks_triplet: tuple[str, str, str],
    rep_frames: list[tuple[int, int]] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """관절 가동범위를 인위적으로 제한한다.

    관절각이 restriction_deg를 초과하는 프레임에서 원위 랜드마크를
    관절각이 restriction_deg가 되도록 조정한다.

    Parameters
    ----------
    df : pd.DataFrame
        원본 정규화 좌표 또는 raw 좌표 포함 데이터프레임.
    joint : str
        제한할 관절 이름 (로그용).
    restriction_deg : float
        허용 최대 관절각 (포함각, 도 단위).
        예: 90.0이면 무릎이 90° 이상 굴곡 불가.
    landmarks_triplet : tuple[str, str, str]
        (proximal_lm, vertex_lm, distal_lm) 랜드마크 이름.
    rep_frames : list[tuple[int, int]], optional
        ROM 제한을 적용할 반복 구간 목록. None이면 전체 시퀀스 적용.

    Returns
    -------
    (restricted_df, simulation_log)

    Notes
    -----
    이 함수는 raw 좌표 컬럼(`<lm>_x/y/z`)을 직접 수정한다.
    정규화 좌표(`<lm>_norm_x/y/z`)는 재계산이 필요하다.
    """
    prox_lm, vert_lm, dist_lm = landmarks_triplet
    df_out = df.copy()

    limit_rad = np.radians(restriction_deg)
    num_restricted = 0

    def _xyz(row_df: pd.DataFrame, lm: str) -> np.ndarray:
        return row_df[[f"{lm}_x", f"{lm}_y", f"{lm}_z"]].values.astype(float)

    # 적용 프레임 결정
    if rep_frames is not None:
        apply_mask = pd.Series(False, index=df_out.index)
        for s, e in rep_frames:
            apply_mask |= (df_out["frame"] >= s) & (df_out["frame"] <= e)
    else:
        apply_mask = pd.Series(True, index=df_out.index)

    for idx in df_out.index[apply_mask]:
        row = df_out.loc[[idx]]
        p = _xyz(row, prox_lm)[0]
        v = _xyz(row, vert_lm)[0]
        d = _xyz(row, dist_lm)[0]

        vp = p - v
        vd = d - v
        norm_p = np.linalg.norm(vp)
        norm_d = np.linalg.norm(vd)

        if norm_p < 1e-9 or norm_d < 1e-9:
            continue

        cos_a = np.clip(np.dot(vp, vd) / (norm_p * norm_d), -1.0, 1.0)
        angle_rad = np.arccos(cos_a)

        # 관절각이 제한값 초과 → 원위 랜드마크를 제한 각도로 조정
        if angle_rad > limit_rad:
            # 원위 방향 벡터를 proximal 방향과 limit_rad 각도를 이루도록 회전
            # 2D 근사: proximal-vertex 평면에서 회전
            vp_unit = vp / norm_p
            # Gram-Schmidt로 평면 내 수직 방향 산출
            perp = vd - np.dot(vd, vp_unit) * vp_unit
            perp_norm = np.linalg.norm(perp)
            if perp_norm < 1e-9:
                continue
            perp_unit = perp / perp_norm
            # 새 원위 방향 = cos(limit) * vp_unit + sin(limit) * perp_unit (flip: 굴곡 방향)
            new_vd_unit = np.cos(limit_rad) * vp_unit + np.sin(limit_rad) * perp_unit
            new_d = v + norm_d * new_vd_unit

            df_out.loc[idx, f"{dist_lm}_x"] = round(float(new_d[0]), 5)
            df_out.loc[idx, f"{dist_lm}_y"] = round(float(new_d[1]), 5)
            df_out.loc[idx, f"{dist_lm}_z"] = round(float(new_d[2]), 5)
            num_restricted += 1

    log: dict[str, Any] = {
        "simulation": "rom_restriction",
        "joint": joint,
        "restriction_deg": restriction_deg,
        "landmarks_triplet": list(landmarks_triplet),
        "num_frames_restricted": num_restricted,
        "rep_frames": rep_frames,
    }
    return df_out, log


# ── 합성 squat 데이터 생성 (generate_synthetic_squat.py 통합) ────────────────

def generate_squat_csv(out_dir, fps: int = 30, seed: int = 20260503) -> None:
    """합성 스쿼트 포즈 CSV를 생성한다.

    simulation/synthetic.py로 이전된 generate_synthetic_squat.py 의 main() 함수.
    기존 data/sample/ 디렉터리 경로를 유지하기 위해 out_dir을 인수로 받는다.

    Parameters
    ----------
    out_dir : Path-like
        출력 디렉터리 (예: Path("data/sample")).
    fps : int
    seed : int
    """
    import csv as _csv
    from pathlib import Path as _Path

    from movement.generate_synthetic_squat import (
        BOTTOM_DELTAS,
        LANDMARKS,
        STANDING_POSE,
        build_frame,
        squat_phase,
    )

    out_dir = _Path(out_dir)
    rng = np.random.default_rng(seed=seed)

    SEGMENTS = [
        ("baseline",    0,  14, False, 1, None),
        ("rep",        15,  59, True,  1, 1),
        ("transition", 60,  74, False, None, None),
        ("rep",        75, 119, True,  1, 2),
    ]
    n_frames = SEGMENTS[-1][2] + 1

    pose_path = out_dir / "mediapipe_squat_synthetic.csv"
    pose_path.parent.mkdir(parents=True, exist_ok=True)
    header = ["frame", "timestamp"]
    for lm in LANDMARKS:
        header += [f"{lm}_x", f"{lm}_y", f"{lm}_z", f"{lm}_visibility"]

    with pose_path.open("w", newline="", encoding="utf-8") as f:
        writer = _csv.writer(f)
        writer.writerow(header)
        for frame_idx in range(n_frames):
            s = 0.0
            for kind, start, end, _use, _set, _rep in SEGMENTS:
                if start <= frame_idx <= end:
                    s = squat_phase(frame_idx, start, end) if kind == "rep" else 0.0
                    break
            row = [frame_idx, round(frame_idx / fps, 4)]
            fd = build_frame(s, rng)
            for lm in LANDMARKS:
                row += list(fd[lm])
            writer.writerow(row)

    ann_path = out_dir / "mediapipe_squat_synthetic_annotation.csv"
    with ann_path.open("w", newline="", encoding="utf-8") as f:
        writer = _csv.writer(f)
        writer.writerow(["segment_type", "set_id", "rep_id", "start_frame",
                          "end_frame", "use_for_analysis", "exercise_type",
                          "pattern", "note"])
        for kind, start, end, use, set_id, rep_id in SEGMENTS:
            note = {
                "baseline":   "standing posture before movement",
                "rep":        f"descent and ascent cycle {rep_id}",
                "transition": "brief pause between reps",
            }.get(kind, "")
            writer.writerow([
                kind,
                set_id if set_id is not None else "",
                rep_id if rep_id is not None else "",
                start, end,
                "true" if use else "false",
                "squat", "bilateral", note,
            ])
