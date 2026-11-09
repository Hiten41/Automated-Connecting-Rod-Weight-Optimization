from pathlib import Path
from conrod.visualization import nondominated


def test_actual_frontier():
    assert nondominated([1, 2, 3, 1], [3, 2, 3, 4]).tolist() == [
        True,
        True,
        False,
        False,
    ]


def test_no_fabricated_contour():
    source = (Path(__file__).parents[1] / "src/conrod/visualization.py").read_text()
    assert "np.sin" not in source and "intensity=" not in source
