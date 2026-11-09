import joblib
import numpy as np
import pytest
from conrod.surrogate import Surrogate, FEATURES
from conrod.schemas import GEOMETRY_VERSION


class LinearFixture:
    def predict(self, x):
        return np.column_stack([x[:, 3] * 10 + 100, x[:, 3] * 0.01])


def test_precision_and_serialization(g, m, load, tmp_path):
    p = tmp_path / "model.joblib"
    joblib.dump(
        dict(
            model=LinearFixture(),
            metadata=dict(
                features=FEATURES,
                geometry_version=GEOMETRY_VERSION,
                supported_min=[-1e9] * len(FEATURES),
                supported_max=[1e9] * len(FEATURES),
            ),
        ),
        p,
    )
    s = Surrogate(p)
    from dataclasses import replace

    a = s.predict(g, m, load)
    b = s.predict(replace(g, ring_thickness=g.ring_thickness + 1e-7), m, load)
    gradient = (b["max_von_mises_mpa"] - a["max_von_mises_mpa"]) / 1e-7
    assert gradient == pytest.approx(10, rel=1e-5)
    # Original 2dp stress rounding destroys this finite difference.
    assert round(b["max_von_mises_mpa"], 2) == round(a["max_von_mises_mpa"], 2)


def test_near_geometry_grouping_across_rounding_boundary(g):
    from dataclasses import replace
    from conrod.surrogate import geometry_groups

    rows = [
        {"geometry": replace(g, ring_thickness=v).to_dict()}
        for v in [6.0499, 6.0501, 8.0]
    ]
    groups = geometry_groups(rows)
    assert groups[0] == groups[1] and groups[0] != groups[2]
