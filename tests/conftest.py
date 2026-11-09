import pytest
from conrod.schemas import Geometry, LoadCase
from conrod.materials import MATERIALS


@pytest.fixture
def g():
    return Geometry()


@pytest.fixture
def m():
    return next(iter(MATERIALS.values()))


@pytest.fixture
def load():
    return LoadCase()
