"""Zero-offset rigid slider-crank; SI internally, compression-positive rod force.

theta=0 is firing TDC; displacement/acceleration positive towards crank.
Fgas - C*cos(beta) = m*a. No friction, gravity, rod bending or rotating inertia.
"""

from dataclasses import dataclass, asdict
import math
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Engine:
    bore_mm: float = 85.99
    stroke_mm: float = 86.0
    rod_length_mm: float = 143.5
    rpm: float = 1500.0
    reciprocating_mass_kg: float = 0.5778
    cycle_deg: int = 720

    def validate(self):
        if not all(math.isfinite(v) for v in asdict(self).values()):
            raise ValueError("Engine inputs must be finite")
        if min(self.bore_mm, self.stroke_mm, self.rod_length_mm) <= 0:
            raise ValueError("Dimensions must be positive")
        if self.rod_length_mm <= self.stroke_mm / 2:
            raise ValueError("Require rod length > crank radius")
        if min(self.rpm, self.reciprocating_mass_kg) < 0 or self.cycle_deg not in (
            360,
            720,
        ):
            raise ValueError("Nonnegative RPM/mass and 360/720 degree cycle required")
        return self


def kinematics(engine, angle_deg):
    e = engine.validate()
    theta = np.deg2rad(np.asarray(angle_deg, dtype=float))
    if not np.isfinite(theta).all():
        raise ValueError("Nonfinite angle")
    r, l = e.stroke_mm / 2000, e.rod_length_mm / 1000
    w = e.rpm * 2 * np.pi / 60
    sn, cs = np.sin(theta), np.cos(theta)
    q = np.sqrt(l * l - r * r * sn * sn)
    x = r * cs + q
    dx = -r * sn - r * r * sn * cs / q
    ddx = -r * cs - r * r * (cs * cs - sn * sn) / q - r**4 * sn * sn * cs * cs / q**3
    return dict(
        displacement_m=r + l - x,
        velocity_m_s=-w * dx,
        acceleration_m_s2=-w * w * ddx,
        approximate_acceleration_m_s2=r * w * w * (cs + r / l * np.cos(2 * theta)),
        beta_rad=np.arcsin(r / l * sn),
    )


def pressure_csv(source, unit="bar", cycle_deg=720):
    """CSV angle_deg,pressure[,reference_pressure], full endpoints mandatory.

    Pressures use the same stated unit. Reference defaults to zero: input then
    represents differential pressure, NOT assumed absolute cylinder pressure.
    Linear interpolation is non-overshooting; no extrapolation or gap filling.
    """
    factors = {"Pa": 1.0, "bar": 1e5, "MPa": 1e6}
    if unit not in factors or cycle_deg not in (360, 720):
        raise ValueError("Use Pa/bar/MPa and a 360/720 degree cycle")
    frame = pd.read_csv(source)
    if not {"angle_deg", "pressure"}.issubset(frame):
        raise ValueError("CSV needs angle_deg and pressure columns")
    frame = frame.sort_values("angle_deg")
    a = frame.angle_deg.to_numpy(dtype=float)
    p = frame.pressure.to_numpy(dtype=float) * factors[unit]
    ref = (
        frame.get("reference_pressure", pd.Series(np.zeros(len(a)))).to_numpy(
            dtype=float
        )
        * factors[unit]
    )
    if len(a) < 3 or not np.isfinite(np.c_[a, p, ref]).all() or np.any(np.diff(a) <= 0):
        raise ValueError("Need >=3 finite, unique angle samples")
    if a[0] != 0 or a[-1] != cycle_deg:
        raise ValueError(
            "Pressure must cover exactly 0 through cycle_deg; no extrapolation"
        )
    if not np.isclose(p[0] - ref[0], p[-1] - ref[-1], rtol=0.01, atol=100):
        raise ValueError(
            "Pressure differential endpoints are not periodic within 1%/100 Pa"
        )
    return pd.DataFrame(dict(angle_deg=a, pressure_pa=p, reference_pa=ref))


def calculate(engine, pressure, step_deg=0.25):
    e = engine.validate()
    if not math.isfinite(step_deg) or not 0 < step_deg <= 10:
        raise ValueError("Angle resolution must be in (0,10] degrees")
    # Revalidate already-normalized data through the same public contract.
    import io

    normalized = pressure.rename(
        columns={"pressure_pa": "pressure", "reference_pa": "reference_pressure"}
    )
    p = pressure_csv(io.StringIO(normalized.to_csv(index=False)), "Pa", e.cycle_deg)
    angle = np.linspace(0, e.cycle_deg, math.ceil(e.cycle_deg / step_deg) + 1)
    k = kinematics(e, angle)
    cylinder = np.interp(angle, p.angle_deg, p.pressure_pa)
    reference = np.interp(angle, p.angle_deg, p.reference_pa)
    gas = (cylinder - reference) * np.pi * (e.bore_mm / 1000) ** 2 / 4
    inertia = -e.reciprocating_mass_kg * k["acceleration_m_s2"]
    rod = (gas + inertia) / np.cos(k["beta_rad"])
    frame = pd.DataFrame(
        dict(
            angle_deg=angle,
            **k,
            pressure_pa=cylinder,
            reference_pa=reference,
            gas_force_n=gas,
            inertia_force_n=inertia,
            rod_compression_n=rod,
        )
    )
    imax, imin = int(np.argmax(rod)), int(np.argmin(rod))
    peaks = dict(
        compression_n=max(0.0, float(rod[imax])),
        tension_n=max(0.0, float(-rod[imin])),
        compression_angle_deg=float(angle[imax]),
        tension_angle_deg=float(angle[imin]),
        compression_components=frame.iloc[imax].to_dict(),
        tension_components=frame.iloc[imin].to_dict(),
        max_abs_acceleration_m_s2=float(np.max(np.abs(k["acceleration_m_s2"]))),
        max_abs_inclination_deg=float(np.rad2deg(np.max(np.abs(k["beta_rad"])))),
        sign_convention="Rod compression positive; FEA tension positive = negative rod force",
        engine=asdict(e),
        step_deg=step_deg,
    )
    return frame, peaks


def plots(frame):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    panels = [
        ("pressure_pa", "Pressure (Pa)"),
        ("displacement_m", "Displacement (m)"),
        ("velocity_m_s", "Velocity (m/s)"),
        ("acceleration_m_s2", "Acceleration (m/s²)"),
        ("gas_force_n", "Gas force (N)"),
        ("inertia_force_n", "Inertia contribution (N)"),
        ("rod_compression_n", "Rod force (N), compression +"),
    ]
    fig = make_subplots(rows=7, cols=1, shared_xaxes=True, vertical_spacing=0.035)
    for row, (key, label) in enumerate(panels, 1):
        fig.add_trace(
            go.Scatter(x=frame.angle_deg, y=frame[key], name=label), row=row, col=1
        )
        fig.update_yaxes(title_text=label, row=row, col=1)
    for idx in [frame.rod_compression_n.idxmax(), frame.rod_compression_n.idxmin()]:
        fig.add_trace(
            go.Scatter(
                x=[frame.loc[idx, "angle_deg"]],
                y=[frame.loc[idx, "rod_compression_n"]],
                mode="markers",
                marker=dict(size=10),
                name="Peak",
            ),
            row=7,
            col=1,
        )
    fig.update_xaxes(title_text="Crank angle after firing TDC (degrees)", row=7, col=1)
    fig.update_layout(height=1500, showlegend=False)
    return fig
