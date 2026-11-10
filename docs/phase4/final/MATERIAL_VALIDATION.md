# Material validation and allowable

## Design assumption retained

All Phase 4 acceptance calculations use the existing project inputs for AISI 4340: E=205 GPa, ν=0.29, density=7850 kg/m³, yield=710 MPa. The project’s required FoS is 1.8, so the von Mises allowable is

\[
\sigma_{allow}=710/1.8=394.444\ \mathrm{MPa}.
\]

This is a historical project assumption, not a heat-treatment certificate for a production connecting rod. No higher strength was substituted to make the design pass.

## Published reference and its limits

The [Atlas Steels 4340 bar data sheet (revised 10 September 2021)](https://atlassteels.com.au/wp-content/uploads/2021/09/Through-Hardening-Low-Alloy-Steel-Bar-4340-Grade-Data-Sheet-10-09-21-1.pdf) describes supplied 4340 bar as hardened and tempered. Its minimum 0.2% proof stress depends on bar diameter/condition: 835 MPa at ≤60 mm, 740 MPa above 60 to 100 mm, 720 MPa above 100 to 178 mm, and 690 MPa above 178 to 240 mm. The sheet gives tensile-strength bands of 1000–1150 MPa for the ≤60 mm condition and 930–1080 MPa for the 60–178 mm conditions. It also describes quench-and-temper processing, with tempering selected to obtain the desired mechanical properties.

These bar values do not identify the forged/machined rod’s actual section size, heat-treatment cycle, lot, hardness, decarburization, residual stress or coupon properties. The sheet does not provide a rod-specific fatigue S–N curve or duty-cycle spectrum. E, ν and density remain project model inputs because this source does not establish the particular component’s certified values.

## Sensitivity context only

For context, dividing the Atlas minimum proof stresses by the project FoS of 1.8 gives reference-only allowables of 463.9, 411.1, 400.0 and 383.3 MPa for the four diameter bands. They are not used for acceptance. The Phase 4 design remains checked against 394.444 MPa based on the required 710 MPa historical assumption.

At the final Phase 4 raw peak of 366.006 MPa, the nominal yield FoS on the project assumption is 1.940. No fatigue qualification is made: validated S–N data, stress-cycle history, surface/process factors and mission life are unavailable.
