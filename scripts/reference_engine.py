"""Reproduce a literature comparison; no experimental validation claim."""

import json
import numpy as np
import pandas as pd
from conrod.engine import Engine, calculate, kinematics, plots
from conrod.fea import ROOT


def run():
    source = ROOT / "data/reference_engine"
    out = ROOT / "runs/reference-engine"
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((source / "metadata.json").read_text())
    e = Engine(**meta["engine"])
    observed = pd.read_csv(source / "mufti_fig7_2_readings.csv")
    area = np.pi * (e.bore_mm / 1000) ** 2 / 4
    pressure = pd.DataFrame(
        dict(
            angle_deg=observed.angle_deg,
            pressure_pa=observed.gas_force_n / area,
            reference_pa=0.0,
        )
    )
    frame, peaks = calculate(e, pressure)
    predicted = np.interp(observed.angle_deg, frame.angle_deg, frame.rod_compression_n)
    observed["calculated_rod_compression_n"] = predicted
    observed["difference_n"] = predicted - observed.measured_rod_force_n
    # Independently read Fig7.4 1500rpm values, +/-50 N visual uncertainty.
    ia = np.array([0, 90, 180, 270, 360])
    inertia_ref = np.array([-780, 200, 440, 200, -800])
    inertia = -e.reciprocating_mass_kg * kinematics(e, ia)["acceleration_m_s2"]
    # Independent geometric identities, plus finite differences of the position expression.
    a = np.arange(0, 720, 5.0)
    h = 0.001
    d = kinematics(e, a)["displacement_m"]
    fd = (
        (
            kinematics(e, a + np.rad2deg(h))["displacement_m"]
            - 2 * d
            + kinematics(e, a - np.rad2deg(h))["displacement_m"]
        )
        / h**2
        * (e.rpm * 2 * np.pi / 60) ** 2
    )
    exact = kinematics(e, a)["acceleration_m_s2"]
    report = dict(
        status="PARTIAL_REFERENCE_COMPARISON_NOT_EXPERIMENTALLY_VALIDATED",
        peaks=peaks,
        observed_rod_peak_n=float(observed.measured_rod_force_n.max()),
        rod_comparison_mae_n=float(np.mean(abs(observed.difference_n))),
        gas_force_check="Round trip F/A to pressure to F is a unit consistency check, NOT independent validation",
        inertia_comparison=dict(
            angle_deg=ia.tolist(),
            published_approximate_n=inertia_ref.tolist(),
            calculated_n=inertia.tolist(),
            reading_uncertainty_n=50,
        ),
        kinematics=dict(
            max_finite_difference_error_m_s2=float(max(abs(fd - exact))),
            tdc_m=float(kinematics(e, [0])["displacement_m"][0]),
            bdc_m=float(kinematics(e, [180])["displacement_m"][0]),
        ),
        metadata=meta,
    )
    frame.to_csv(out / "cycle.csv", index=False)
    pressure.rename(
        columns={"pressure_pa": "pressure", "reference_pa": "reference_pressure"}
    ).to_csv(out / "pressure_Pa_APPROXIMATE.csv", index=False)
    observed.to_csv(out / "comparison.csv", index=False)
    (out / "report.json").write_text(json.dumps(report, indent=2))
    plots(frame).write_html(out / "engine.html", include_plotlyjs=True)
    print(json.dumps({k: v for k, v in report.items() if k != "metadata"}, indent=2))
    return report


if __name__ == "__main__":
    run()
