from dataclasses import replace
import pytest
from conrod.materials import MATERIALS, mass_from_volume


@pytest.mark.parametrize("material", list(MATERIALS.values()))
def test_material(material):
    material.validate()
    assert mass_from_volume(1000, material) == pytest.approx(
        1000 * material.density_kg_per_mm3
    )


def test_density_scaling(m):
    assert mass_from_volume(
        1000, replace(m, density_kg_per_mm3=2 * m.density_kg_per_mm3)
    ) == pytest.approx(2 * mass_from_volume(1000, m))


def test_reject_bad_material(m):
    with pytest.raises(ValueError):
        replace(m, poissons_ratio=0.5).validate()
