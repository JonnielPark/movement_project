from pathlib import Path

import yaml


CAMERA_ZONES_PATH = Path("data/camera/camera_zones.yaml")
CAMERA_PROTOCOLS_DIR = Path("data/protocols/camera")


def test_camera_zones_use_polar_ring_model():
    config = yaml.safe_load(CAMERA_ZONES_PATH.read_text(encoding="utf-8"))

    assert config["zone_model"] == "polar_camera_ring"
    assert config["coordinate_reference"] == "reference_origin"
    assert config["origin"]["label"] == "subject_or_reference_mat_center"
    assert config["default_distance_cm"] == [200, 250]
    assert config["default_azimuth_tolerance_deg"] == 10
    assert config["anchor"]["reference_mat"]["front_guidance"]
    assert config["anchor"]["reference_mat"]["rear_guidance"]
    assert config["anchor"]["reference_mat"]["front_oblique_guidance"]
    assert config["anchor"]["reference_mat"]["rear_oblique_guidance"]
    assert config["anchor"]["reference_mat"]["side_guidance"]

    assert set(config["zones"]) == {f"Z{i}" for i in range(1, 9)}

    for zone_id, zone in config["zones"].items():
        assert "azimuth_deg" in zone, zone_id
        assert zone["azimuth_tolerance_deg"] == 10
        assert zone["distance_cm"] == [200, 250]
        assert "offset_cm" not in zone
        assert "lateral_tolerance_cm" not in zone
        assert "anterior_tolerance_cm" not in zone


def test_camera_zone_azimuths_match_expected_viewpoints():
    config = yaml.safe_load(CAMERA_ZONES_PATH.read_text(encoding="utf-8"))

    azimuths = {
        zone_id: zone["azimuth_deg"] for zone_id, zone in config["zones"].items()
    }

    assert azimuths == {
        "Z1": 0,
        "Z2": 45,
        "Z3": 90,
        "Z4": 135,
        "Z5": 180,
        "Z6": -135,
        "Z7": -90,
        "Z8": -45,
    }


def test_camera_view_families_group_mirror_equivalent_zones():
    config = yaml.safe_load(CAMERA_ZONES_PATH.read_text(encoding="utf-8"))

    families = config["view_families"]

    assert families["front_oblique"]["member_zones"] == ["Z2", "Z8"]
    assert families["front_oblique"]["mirror_equivalent"] is True
    assert families["side"]["member_zones"] == ["Z3", "Z7"]
    assert families["side"]["mirror_equivalent"] is True
    assert families["rear_oblique"]["member_zones"] == ["Z4", "Z6"]
    assert families["rear_oblique"]["mirror_equivalent"] is True


def test_target_exercise_camera_protocol_recommended_zones():
    expected_zones = {
        "squat": ["Z2", "Z8"],
        "plank_shoulder_tap": ["Z2", "Z8"],
        "lunge": ["Z3", "Z7"],
        "pike_pushup": ["Z3", "Z7"],
    }

    for exercise_id, zones in expected_zones.items():
        protocol = yaml.safe_load(
            (CAMERA_PROTOCOLS_DIR / f"{exercise_id}.yaml").read_text(encoding="utf-8")
        )

        assert protocol["camera_protocol"]["recommended_zones"] == zones
