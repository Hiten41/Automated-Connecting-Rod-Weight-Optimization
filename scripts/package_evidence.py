"""Portable copies and SHA256 manifest; raw run records are never rewritten."""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import subprocess
from conrod.fea import ROOT


def portable(value):
    if isinstance(value, dict):
        return {k: portable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [portable(v) for v in value]
    if isinstance(value, str):
        try:
            path = Path(value)
            if path.is_absolute():
                return path.relative_to(ROOT).as_posix()
        except (ValueError, OSError):
            pass
    if isinstance(value, str):
        return value.replace(str(ROOT), ".")
    return value


def package(destination, include_fields=False):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    entries = []
    omitted_fields = []
    suffixes = {
        ".json",
        ".csv",
        ".inp",
        ".log",
        ".step",
        ".stl",
        ".fcstd",
        ".md",
        ".joblib",
        ".jsonl",
        ".png",
        ".xml",
        ".html",
    }
    for directory in [
        "runs/phase2-experiments",
        "runs/focused-refinement",
        "runs/engine-example",
        "runs/fillet-feasibility",
        "runs/phase2-optimization",
        "runs/phase2-diagnostic-verification",
        "runs/reference-engine",
        "data/phase2",
        "models",
        "evidence/phase2",
        "data/reference_engine",
        "docs",
    ]:
        for source in (ROOT / directory).rglob("*"):
            if not source.is_file() or source.suffix.lower() not in suffixes:
                continue
            if source.name == "fields.json" and not include_fields:
                h = hashlib.sha256()
                with source.open("rb") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        h.update(block)
                omitted_fields.append(
                    dict(
                        path=source.relative_to(ROOT).as_posix(),
                        sha256=h.hexdigest(),
                        bytes=source.stat().st_size,
                        available="original local run folder; use --fields to include",
                    )
                )
                continue
            relative = source.relative_to(ROOT).as_posix()
            raw = source.read_bytes()
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix == ".json":
                try:
                    target.write_text(
                        json.dumps(portable(json.loads(raw)), indent=2),
                        encoding="utf-8",
                    )
                except (ValueError, UnicodeDecodeError):
                    target.write_bytes(raw)
            else:
                target.write_bytes(raw)
            entries.append(
                dict(
                    path=relative,
                    raw_sha256=hashlib.sha256(raw).hexdigest(),
                    export_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                    bytes=target.stat().st_size,
                )
            )
    manifest = dict(
        schema="phase2-portable-evidence-v1",
        git_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        entries=entries,
        omitted_fields=omitted_fields,
        includes_fields=include_fields,
        note="Raw records remain unchanged; exported JSON paths are relative to project root. Hashes distinguish raw and portable copies.",
    )
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("destination")
    p.add_argument("--fields", action="store_true")
    p.add_argument("--zip", action="store_true")
    a = p.parse_args()
    manifest = package(a.destination, a.fields)
    if a.zip:
        with zipfile.ZipFile(
            str(a.destination) + ".zip", "w", zipfile.ZIP_DEFLATED
        ) as z:
            for f in Path(a.destination).rglob("*"):
                if f.is_file():
                    z.write(f, f.relative_to(a.destination))
    print(f"Packaged {len(manifest['entries'])} artifacts")
