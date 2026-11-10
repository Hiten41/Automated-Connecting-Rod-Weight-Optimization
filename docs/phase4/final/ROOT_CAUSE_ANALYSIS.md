# Root cause analysis

See the full raw-field investigation in [the Phase 4 root cause report](../ROOT_CAUSE_ANALYSIS.md). The controlling Phase 3 peaks are at the big-end/shank transition: 566.718 MPa compression and 770.139 MPa tension, against a 394.444 MPa allowable. The cause is local three-dimensional load transfer through a small eye-to-shank fillet, rather than uniform shank axial stress. The prescribed COSINE_BEARING boundary condition is an equivalent pressure model, not pin contact.
