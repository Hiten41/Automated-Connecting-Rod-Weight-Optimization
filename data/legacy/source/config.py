import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")

for directory in [DATA_DIR, MODEL_DIR, EXPORT_DIR]:
    os.makedirs(directory, exist_ok=True)

DATASET_PATH = os.path.join(DATA_DIR, "connecting_rod_fea_dataset.csv")
SURROGATE_MODEL_PATH = os.path.join(MODEL_DIR, "nn_surrogate_model.pkl")

# Path to FreeCAD headless executable (Update according to your OS installation)
# Windows typical: r"C:\Program Files\FreeCAD 0.21\bin\freecadcmd.exe"
# Linux typical: "/usr/bin/freecadcmd"
FREECAD_CMD_PATH = r"C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe"
# Parametric Bounds for Connecting Rod Geometry (in mm)
PARAM_BOUNDS = {
    "length_cc": (125.0, 165.0),       # Center-to-center length (Fixed per user spec during optimization)
    "big_end_id": (44.0, 56.0),        # Crankpin bore inner diameter (Fixed per user spec)
    "small_end_id": (20.0, 28.0),      # Piston pin bore inner diameter (Fixed per user spec)
    "ring_thickness": (4.5, 9.0),      # Wall thickness around big & small ends (Optimizable)
    "shank_width": (15.0, 28.0),       # Width of connecting rod I-beam shank (Optimizable)
    "beam_thickness": (14.0, 24.0),    # Extrusion height / thickness of rod (Optimizable)
    "pocket_depth": (2.0, 6.0),        # Depth of lightweighting I-beam pocket on each side (Optimizable)
    "flange_thickness": (2.5, 6.0),    # Thickness of I-beam flange wall (Optimizable)
}

# Material Library for Automotive Connecting Rods
MATERIALS = {
    "Forged Steel (AISI 4340)": {
        "youngs_modulus_mpa": 205000.0,
        "poissons_ratio": 0.29,
        "density_kg_mm3": 7.85e-6,
        "yield_strength_mpa": 710.0,
    },
    "Titanium Alloy (Ti-6Al-4V)": {
        "youngs_modulus_mpa": 113800.0,
        "poissons_ratio": 0.34,
        "density_kg_mm3": 4.43e-6,
        "yield_strength_mpa": 880.0,
    },
    "Forged Aluminum (7075-T6)": {
        "youngs_modulus_mpa": 71700.0,
        "poissons_ratio": 0.33,
        "density_kg_mm3": 2.81e-6,
        "yield_strength_mpa": 503.0,
    },
}