# Engine loading and reference validation

`engine.py` uses SI internally. Crank angle zero is firing TDC. The piston coordinate toward the cylinder head is x=r cos(theta)+sqrt(l²-r² sin²(theta)); displacement toward the crank is s=r+l-x. At constant omega=2*pi*RPM/60, v=-omega*x' and a=-omega²*x''. With q=sqrt(l²-r² sin²(theta)), x''=-r cos(theta)-r² cos(2theta)/q-r⁴ sin²(theta)cos²(theta)/q³. The familiar approximation is a=r omega²[cos(theta)+(r/l)cos(2theta)].

Piston equilibrium is Fgas-C cos(beta)=m a, sin(beta)=(r/l)sin(theta). Thus compression-positive rod force C=(Fgas-m a)/cos(beta). Fgas=(pcylinder-preference)*pi*D²/4. The FEA signed force convention is opposite: tension positive. Peaks are extracted independently over the complete cycle; their gas/inertia components and crank angles are retained. Zero RPM removes inertia, not gas force.

Effective reciprocating mass is an input, not the entire CAD rod mass. No additional structural body inertia is applied in the static FEA, avoiding double counting. This ideal mechanism excludes friction, gravity, pin offset, elastic dynamics, rotating rod inertia, bearing clearance and transient stresses. It is not a complete dynamic cranktrain solution.

## CSV contract

Columns: `angle_deg,pressure,reference_pressure` (last optional). Explicit unit Pa, bar or MPa applies to both pressures. Missing reference means pressure is already differential; no atmospheric assumption is made. Require finite unique samples spanning exactly 0..360 or 0..720 and differential endpoints matching within 1%/100 Pa. Linear interpolation cannot overshoot; extrapolation is prohibited. Sparse samples remain sparse evidence, even when a dense evaluation grid is used.

## Public automobile-derived reference

Reference: Ricardo Hydra single-cylinder gasoline research engine derived from the GM 2.0 litre Cavalier engine, **not a stock Cavalier assembly**.

Sources:

- Riaz Ahmad Mufti, University of Leeds PhD (2004), [Total and component friction in a motored and firing engine](https://etheses.whiterose.ac.uk/id/eprint/5354/1/414535.pdf). Printed p114: automobile lineage and measured bore 85.99 mm. Fig7.2 (p143/PDF168): synchronized gas and rod force at 1500 RPM, half load. Fig7.4 (p146/PDF171): piston-assembly inertia, mass 577.8 g.
- Mufti and Priest (2009), [Effect of Engine Operating Conditions and Lubricant Rheology on the Distribution of Losses in an Internal Combustion Engine](https://doi.org/10.1115/1.3176988), Table1: stroke86 mm, rod143.5 mm. The published effective reciprocating mass0.64 kg is a different definition and is not substituted for Fig7.4's piston assembly. [Author paper mirror](https://citeseerx.ist.psu.edu/document?doi=7067fabec0c2fbf5a2c4c7a293ee0e0a131718dd&repid=rep1&type=pdf).
- [Dyson (2011), Table6.1](https://etheses.whiterose.ac.uk/id/eprint/2772/1/Dyson_CJ_Mechanical_Engineering_PhD_2011.pdf) corroborates86 mm stroke/143.5 mm rod for the Leeds Hydra family, but also reports1 mm pin offset. Our zero-offset approximation does not reproduce that feature.

The thesis geometry appendix was supplied on a CD-ROM absent from the public PDF. Identical build configuration cannot be established across publications. Exact torque, spark timing, mixture and thermal conditions for Fig7.2 are not specified in its caption. No raw cylinder-pressure-versus-angle dataset was obtained.

`data/reference_engine/mufti_fig7_2_readings.csv` contains approximate manual readings of the visibly inspected published graph. Estimated reading uncertainty is +/-150 N and +/-5 degrees, not a statistical confidence interval. Gas force is divided by piston area to form approximate differential pressure; this is not the original absolute sensor trace. Conversion back to force is only a unit round-trip check, not independent validation. The independently plotted rod curve is compared without fitting the model to it. Section-B rod inertia, friction, gravity and measurement conventions differ from ideal piston-side axial force.

Run `python scripts/reference_engine.py`. It saves cycle CSV, pressure reconstruction, independent rod comparison, inertia comparison with Fig7.4, finite-difference kinematic checks, and an interactive plot. The outcome is explicitly PARTIAL_REFERENCE_COMPARISON_NOT_EXPERIMENTALLY_VALIDATED. Experiment D uses these loads only as a labelled literature-derived illustrative FEA example. Do not claim experimentally validated combustion loading.


## Phase 3 rod inertia contribution

An optional total rod mass m_r and center-of-mass fraction f measured from the crank pin are now explicit inputs. Equivalent end masses are m_small=m_r*f and m_big=m_r*(1-f), preserving total mass and the first mass moment. Effective axial reciprocating inertia uses (m_piston+m_small)*a. The rotating share is not added to piston inertia. This approximation generally does not preserve the actual rod polar mass moment and cannot recover distributed rod bending or unequal instantaneous end loads; a rigid-body inverse-dynamics extension would need measured mass, center of mass and inertia tensor.

The default additional rod mass is zero. This preserves the published piston-assembly comparison. The reference Hydra rod mass/CG are missing: no arbitrary fraction is presented as measured reference data. Users supplying an already combined effective reciprocating mass must leave the additional rod mass zero to avoid double counting. Tests check mass partition, force equilibrium, invalid mass and unchanged reference behavior.

The 28kN compression and18kN tension requirements remain the structural design envelope. They are legacy design requirements, not established as a measured Hydra operating envelope. The approximate1500RPM half-load literature example is illustrative and substantially smaller; substituting it would change the design question and is not done. An experimentally defensible combustion envelope remains incomplete without pressure traces across operating conditions and documented masses.


## Additional data search

A further search located instrumented Hydra research, including [Ristow Hadlich et al., author proof](https://bpb-us-e1.wpmucdn.com/you.stonybrook.edu/dist/e/1841/files/2024/11/RistowHadlich_et_al_MachineLearning_GTP-23-1668_AuthorProof.pdf). Its compression-ignition configuration has79mm bore and160mm rod length, distinct from the retained Leeds gasoline reference. It is not substituted or combined with the Leeds mass and geometry. No matching raw pressure trace was obtained during this search; the original digitized-plot limitation remains.
