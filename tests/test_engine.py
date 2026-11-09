import io
import numpy as np
import pandas as pd
import pytest
from dataclasses import replace
from conrod.engine import Engine, kinematics, pressure_csv, calculate


def profile(p=1e5):
    return pd.DataFrame(
        dict(
            angle_deg=[0, 180, 360, 540, 720], pressure_pa=[p] * 5, reference_pa=[0] * 5
        )
    )


def test_dead_centers_and_zero_speed():
    e = Engine(rpm=0)
    k = kinematics(e, [0, 180, 360])
    assert np.allclose(k["displacement_m"], [0, 0.086, 0])
    assert np.all(k["velocity_m_s"] == 0)
    assert np.all(k["acceleration_m_s2"] == 0)


def test_derivatives_and_approximation():
    e = Engine(rod_length_mm=10000)
    k = kinematics(e, np.arange(360))
    assert (
        np.max(abs(k["acceleration_m_s2"] - k["approximate_acceleration_m_s2"])) < 0.001
    )
    e = Engine()
    a = np.arange(0, 360, 7)
    h = 0.01
    fd = (
        (kinematics(e, a + h)["velocity_m_s"] - kinematics(e, a - h)["velocity_m_s"])
        / (2 * np.deg2rad(h))
        * (e.rpm * 2 * np.pi / 60)
    )
    assert np.allclose(fd, kinematics(e, a)["acceleration_m_s2"], rtol=1e-6, atol=1e-4)


def test_force_equilibrium_signs_and_scaling():
    e = Engine()
    f, p = calculate(e, profile(0))
    assert p["compression_n"] > 0 and p["tension_n"] > 0
    assert f.rod_compression_n.iloc[0] < 0
    assert np.allclose(
        f.gas_force_n - f.rod_compression_n * np.cos(f.beta_rad),
        e.reciprocating_mass_kg * f.acceleration_m_s2,
    )
    f2, _ = calculate(replace(e, rpm=3000), profile(0))
    assert np.allclose(f2.inertia_force_n, 4 * f.inertia_force_n)
    f3, _ = calculate(replace(e, rpm=0), profile())
    f4, _ = calculate(replace(e, rpm=0, bore_mm=e.bore_mm * 2), profile())
    assert np.allclose(f4.gas_force_n, 4 * f3.gas_force_n)
    assert f3.rod_compression_n.min() > 0


@pytest.mark.parametrize("unit,value", [("bar", 1), ("MPa", 0.1), ("Pa", 100000)])
def test_units(unit, value):
    p = pressure_csv(
        io.StringIO(f"angle_deg,pressure\n0,{value}\n360,{value}\n720,{value}"), unit
    )
    assert np.allclose(p.pressure_pa, 100000)


@pytest.mark.parametrize(
    "csv",
    [
        "angle_deg,pressure\n0,1\n0,2\n720,1",
        "angle_deg,pressure\n0,1\n180,2\n360,1",
        "angle_deg,pressure\n0,1\n360,nan\n720,1",
        "angle_deg,pressure\n0,1\n360,1\n720,3",
    ],
)
def test_bad_pressure(csv):
    with pytest.raises(ValueError):
        pressure_csv(io.StringIO(csv))


def test_invalid_inputs():
    for e in [
        Engine(rpm=-1),
        Engine(rod_length_mm=43),
        Engine(reciprocating_mass_kg=float("nan")),
    ]:
        with pytest.raises(ValueError):
            e.validate()
    with pytest.raises(ValueError):
        pressure_csv(io.StringIO("angle_deg,pressure\n0,1\n360,1\n720,1"), "psi")


def test_linear_interpolation_no_overshoot():
    p = profile(0)
    p.loc[1, "pressure_pa"] = 1e6
    f, peaks = calculate(Engine(rpm=0), p)
    assert f.pressure_pa.max() == 1e6
    assert peaks["compression_angle_deg"] == 180
    assert f.loc[f.angle_deg == 90, "pressure_pa"].iloc[0] == 500000


def test_public_reference_published_inertia_readings():
    # Mufti thesis Fig7.4; independently read points, not an experimental force certification.
    engine = Engine()
    calculated = (
        -engine.reciprocating_mass_kg
        * kinematics(engine, [0, 90, 180, 270, 360])["acceleration_m_s2"]
    )
    published_approximate = np.array([-780, 200, 440, 200, -800])
    assert np.max(abs(calculated - published_approximate)) < 50
