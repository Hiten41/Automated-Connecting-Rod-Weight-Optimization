"""Package and verify reproducible Phase 4 solver evidence."""

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE3 = ROOT.parent / "phase3-rod"
# Preserve the original intake archive at phase4-final-solver-evidence.zip.
OUT = ROOT / "outputs/phase4-final-solver-evidence-final.zip"
INCLUDE_SUFFIXES = {
    ".json",
    ".jsonl",
    ".log",
    ".inp",
    ".dat",
    ".frd",
    ".sta",
    ".cvg",
    ".12d",
    ".msh",
    ".brep",
    ".step",
    ".stl",
    ".fcstd",
    ".md",
    ".png",
    ".csv",
    ".xml",
}
DESIGN_IDS = ("P4-0055", "P4-0026", "P4-0059", "P4-0016", "P4-0060", "P4-0065")


def sha256_stream(stream):
    h = hashlib.sha256()
    size = 0
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(block)
        size += len(block)
    return size, h.hexdigest()


def sha256_file(path):
    with Path(path).open("rb") as stream:
        return sha256_stream(stream)


def add_tree(files, base, arc_prefix, suffixes=INCLUDE_SUFFIXES):
    base = Path(base)
    if not base.exists():
        return
    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in suffixes:
            arcname = Path(arc_prefix) / path.relative_to(base)
            files[str(arcname).replace("\\", "/")] = path


def add_path(files, relative, archive_name=None):
    path = ROOT / relative
    if path.is_file():
        files[(archive_name or relative).replace("\\", "/")] = path


def build_file_manifest(files, readme):
    entries = []
    for name, path in sorted(files.items()):
        size, checksum = sha256_file(path)
        entries.append({"path": name, "size_bytes": size, "sha256": checksum})
    entries.append(
        {
            "path": "README.txt",
            "size_bytes": len(readme),
            "sha256": hashlib.sha256(readme).hexdigest(),
        }
    )
    return entries


def verify_archive(path, source_revision):
    with zipfile.ZipFile(path, "r") as archive:
        manifest = json.loads(archive.read("evidence_manifest.json"))
        if manifest.get("source_revision") != source_revision:
            raise RuntimeError(
                "Manifest source revision does not match the packaged Git revision"
            )
        entries = {item["path"]: item for item in manifest["files"]}
        archive_names = archive.namelist()
        members = set(archive_names) - {"evidence_manifest.json"}
        if len(archive_names) != len(set(archive_names)) or members != set(entries):
            missing = sorted(set(entries) - members)
            unexpected = sorted(members - set(entries))
            raise RuntimeError(
                f"Archive/manifest membership mismatch; missing={missing}, unexpected={unexpected}"
            )
        for name, entry in entries.items():
            with archive.open(name, "r") as stream:
                size, checksum = sha256_stream(stream)
            if size != entry["size_bytes"] or checksum != entry["sha256"]:
                raise RuntimeError(f"SHA-256 or size verification failed for {name}")
    return {"verified_files": len(entries), "source_revision": source_revision}


def main():
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    files = {}

    # Phase 3 baseline CAD and raw stress/displacement fields used in the audit.
    for case in ("0.35-compression", "0.35-tension"):
        add_tree(
            files,
            PHASE3 / "runs/phase3-refinement" / case,
            f"phase3/baseline/{case}",
        )
    add_tree(files, PHASE3 / "evidence/phase3", "phase3/audit")

    # Full candidate CAD, CalculiX decks and results, Gmsh meshes, fields and logs.
    for candidate_id in DESIGN_IDS:
        add_tree(
            files,
            ROOT / "runs/phase4-refined" / candidate_id,
            f"phase4/refined/{candidate_id}",
        )

    # Reproducible seeded and Latin-hypercube exploration, including paired raw FEA.
    for study in ("phase4-design-space", "phase4-design-space-lhs"):
        study_root = ROOT / "runs" / study
        for name in ("manifest.json", "summary.json"):
            path = study_root / name
            if path.exists():
                files[f"phase4/{study}/{name}"] = path
        add_tree(files, study_root / "fea", f"phase4/{study}/fea")

    add_tree(files, ROOT / "data/phase4", "phase4/analysis-data")
    add_tree(
        files,
        ROOT / "data/reference_engine",
        "engine/reference-data",
        suffixes={".json", ".csv"},
    )
    add_tree(files, ROOT / "docs/phase4/final", "phase4/reports")
    add_tree(files, ROOT / "docs/phase4", "phase4/root-cause", suffixes={".md"})
    add_path(files, "docs/ENGINE_LOAD_MODEL.md", "engine/reports/ENGINE_LOAD_MODEL.md")
    add_path(
        files,
        "docs/final/ENGINE_LOAD_VALIDATION.md",
        "engine/reports/ENGINE_LOAD_VALIDATION.md",
    )
    add_path(files, "docs/final/MATERIAL_BASIS.md", "engine/reports/MATERIAL_BASIS.md")
    add_path(files, "scripts/reference_engine.py", "engine/scripts/reference_engine.py")
    add_path(
        files, "scripts/engine_fea_example.py", "engine/scripts/engine_fea_example.py"
    )
    add_path(
        files, "scripts/phase4_browser_qa.cjs", "phase4/scripts/phase4_browser_qa.cjs"
    )
    add_tree(files, ROOT / "outputs/phase4-visual-qa", "visual-qa")

    critical_names = set(files)
    if not any(name.endswith(".frd") for name in critical_names):
        raise RuntimeError("The evidence set has no raw CalculiX .frd fields")
    if not any(name.endswith("fields.json") for name in critical_names):
        raise RuntimeError(
            "The evidence set has no serialized stress/displacement fields"
        )
    if not any(name.endswith(".msh") for name in critical_names):
        raise RuntimeError("The evidence set has no Gmsh mesh files")
    if not any(name.startswith("engine/reference-data/") for name in critical_names):
        raise RuntimeError("The reference-engine calculations/data were not included")
    if not any(name.endswith("all-test-results.xml") for name in critical_names):
        raise RuntimeError("The complete test report is missing from the evidence set")
    if not any(name.endswith("browser-qa-report.json") for name in critical_names):
        raise RuntimeError(
            "The Playwright browser report is missing from the evidence set"
        )

    readme = (
        "Phase 4 solver and visual-QA evidence archive\n"
        f"Source branch: {branch}\n"
        f"Source revision: {revision}\n"
        "\n"
        "Includes Phase 3 baseline CAD and raw fields; Phase 4 candidate CAD, meshes, "
        "CalculiX input decks, raw FRD/DAT outputs and stress/displacement fields; the two "
        "seeded design-space studies; engine reference data/calculations; material and "
        "engineering reports; test reports; Playwright QA report and screenshots.\n"
        "\n"
        "FEA results use unaveraged integration-point von Mises stress for yield screening. "
        "The meshes are nonnested and do not establish a GCI or continuum error bound. "
        "COSINE_BEARING is an equivalent pressure approximation, not nonlinear pin contact. "
        "No production qualification, fatigue life or global optimum is claimed.\n"
    ).encode()
    manifest = {
        "source_branch": branch,
        "source_revision": revision,
        "manifest_scope": "All archive members except evidence_manifest.json itself",
        "files": build_file_manifest(files, readme),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True
    ) as archive:
        archive.writestr("README.txt", readme)
        archive.writestr("evidence_manifest.json", json.dumps(manifest, indent=2))
        for name, path in sorted(files.items()):
            archive.write(path, arcname=name)

    verification = verify_archive(OUT, revision)
    archive_size, archive_hash = sha256_file(OUT)
    print(
        json.dumps(
            {
                "archive": str(OUT),
                "source_branch": branch,
                "source_revision": revision,
                "files_verified": verification["verified_files"],
                "archive_bytes": archive_size,
                "archive_sha256": archive_hash,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
