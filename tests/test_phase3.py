import numpy as np
import pytest
from conrod.fields import regional_stress_report
from conrod.schemas import Geometry, MeshSettings


def test_mixed_simulation_versions_rejected(tmp_path):
    import json
    from conrod.dataset import load_verified
    from test_dataset import record

    a = record()
    b = record()
    b["simulation_version"] = "phase3-deterministic-bearing-v1"
    b["sample_id"] = "new"
    p = tmp_path / "mixed.jsonl"
    p.write_text(json.dumps(a) + "\n" + json.dumps(b), encoding="utf-8")
    with pytest.raises(ValueError, match="provenance"):
        load_verified(p)


def test_constant_tensor_recovery_and_duplicate_rejection():
    corners = np.array(
        [[30, 12, 0], [31, 12, 0], [30, 13, 0], [30, 12, 1]], dtype=float
    )
    points = list(corners) + [
        (corners[i] + corners[j]) / 2
        for i, j in [(0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3)]
    ]
    nodes = {i + 1: p.tolist() for i, p in enumerate(points)}
    elements = {1: list(range(1, 11))}
    stress = [[1, ip, 100, 0, 0, 0, 0, 0] for ip in range(1, 5)]
    result = regional_stress_report(nodes, elements, stress, Geometry())
    assert result["raw_ip_peak_mpa"] == pytest.approx(100)
    assert result["element_mean_tensor_vm_max_mpa"] == pytest.approx(100)
    assert result["regions"]["big_end_transition"]["count"] == 4
    with pytest.raises(ValueError, match="unique"):
        regional_stress_report(nodes, elements, stress[:3] + [stress[0]], Geometry())


def test_refinement_region_validation():
    MeshSettings(
        hotspot_size_mm=0.25, refinement_region="big_end_transition"
    ).validate()
    with pytest.raises(ValueError, match="refinement"):
        MeshSettings(refinement_region="arbitrary").validate()


def test_separate_rod_mass_preserves_partition_and_force_equilibrium():
    from conrod.engine import Engine, calculate
    import pandas as pd

    pressure = pd.DataFrame(
        dict(angle_deg=[0, 360, 720], pressure_pa=[0, 0, 0], reference_pa=[0, 0, 0])
    )
    e = Engine(rod_mass_kg=0.6, rod_cg_fraction_from_crank=0.3)
    frame, peaks = calculate(e, pressure)
    assert peaks["rod_mass_partition"]["reciprocating_kg"] == pytest.approx(0.18)
    assert peaks["rod_mass_partition"]["rotating_kg"] == pytest.approx(0.42)
    np.testing.assert_allclose(
        frame.rod_compression_n * np.cos(frame.beta_rad),
        -(0.5778 + 0.18) * frame.acceleration_m_s2,
        atol=1e-10,
    )
    np.testing.assert_allclose(
        frame.rod_reciprocating_inertia_force_n, -0.18 * frame.acceleration_m_s2
    )
    with pytest.raises(ValueError):
        Engine(rod_mass_kg=-1).validate()
