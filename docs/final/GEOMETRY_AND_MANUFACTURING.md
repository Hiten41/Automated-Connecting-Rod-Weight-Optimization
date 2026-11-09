# Geometry and manufacturing

The baseline keeps145mm center distance,50mm big bore,24mm small bore,8mm ring wall,25mm shank width,22mm beam thickness,2.2mm pockets,5.5mm flanges and1mm transition radius. Its actual FreeCAD mass with the reference density is735.326854g. Actual solid construction has four vertical shank-ring fillets and rounded pocket cutters; bores are cut and identified geometrically. It must remain one valid solid with independent web/flange probes matching inputs.

The feasibility envelope fixes packaging dimensions and varies ring wall4.5–9mm, width15–28mm, thickness14–24mm, pocket depth2–6mm, flange2.5–6mm and radius0.5–3mm. Coupled constraints require web>=3.5mm, pocket width>=4mm, pocket length>5mm and radius smaller than pocket depth, half pocket width and half ring wall. Invalid combinations are recorded rather than silently removed from the sampling plan.

This is a parametric research shape, not a manufacturing release. Tool access, tolerances, surface finish, forging grain flow, big-end splitting/bolts, bearing shells, lubrication holes and fatigue treatment are not fully modeled. A larger fillet cannot be adopted by changing a stress factor alone: it must exist in CAD and pass geometry constraints and FEA. Added CAD center-of-mass metadata permits a uniform-density equivalent end-mass estimate, not a measured Hydra rod mass distribution.
