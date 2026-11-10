"""Build a self-contained source and UI-QA review ZIP for Phase 4."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT / "outputs/phase4-complete-review-bundle/rodLab-phase4-complete-source.zip"
)
PREFIX = "rodLab-phase4"
BRANCH = "feature/phase4-physics-guided-redesign"
BASE = "0981e89f8189814041813b26d9dd4c2f1cd35ef1"
SIZE_LIMIT = 512_000_000
BLOCKED_NAME = re.compile(
    r"(^|/)(\.env($|\.)|[^/]*\.(pem|key|pfx|p12)|credentials?[^/]*|secrets?[^/]*)$",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"sk-[A-Za-z0-9]{24,}"),
)
COMPRESSED_SUFFIXES = {".zip", ".png", ".jpg", ".jpeg", ".gif", ".pkl", ".joblib"}


def sha256_stream(stream) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        size += len(block)
        digest.update(block)
    return size, digest.hexdigest()


def sha256_path(path: Path) -> tuple[int, str]:
    with path.open("rb") as stream:
        return sha256_stream(stream)


def git_value(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def review_files() -> dict[str, Path]:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    files = {}
    for item in tracked.split(b"\0"):
        if item:
            relative = item.decode("utf-8").replace("\\", "/")
            files[f"{PREFIX}/{relative}"] = ROOT / Path(relative)
    qa_root = ROOT / "outputs/phase4-visual-qa"
    if qa_root.is_dir():
        for path in qa_root.rglob("*"):
            if path.is_file():
                files[f"{PREFIX}/visual-qa/{path.relative_to(qa_root).as_posix()}"] = (
                    path
                )
    for name in (
        "all-test-results.xml",
        "integration-test-results.xml",
        "unit-test-results.xml",
    ):
        path = ROOT / "data/phase4" / name
        if path.is_file():
            files[f"{PREFIX}/verification/{name}"] = path
    return files


def scan_secrets(files: dict[str, Path]) -> None:
    potential = []
    for name, path in files.items():
        if BLOCKED_NAME.search(name):
            raise RuntimeError(f"Refusing credential-like path: {name}")
        if (
            path.suffix.lower() in COMPRESSED_SUFFIXES
            or path.stat().st_size > 20_000_000
        ):
            continue
        content = path.read_bytes()
        if b"\0" in content[:4096]:
            continue
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            potential.append(name)
    if potential:
        raise RuntimeError(f"Potential secret-like content found: {potential}")


def main() -> None:
    branch = git_value("branch", "--show-current")
    revision = git_value("rev-parse", "HEAD")
    status = git_value("status", "--porcelain")
    if branch != BRANCH:
        raise RuntimeError(f"Refusing to package branch {branch!r}")
    if git_value("merge-base", "--is-ancestor", BASE, "HEAD"):
        raise RuntimeError("Phase 3 base ancestry check failed")
    if status:
        raise RuntimeError(
            f"Working tree must be clean before source packaging: {status}"
        )

    files = review_files()
    if not files:
        raise RuntimeError("No source or review materials were found")
    scan_secrets(files)
    readme = (
        "RodLab Phase 4 complete source and UI review archive\n"
        f"Branch: {branch}\nRevision: {revision}\nBase: {BASE}\n\n"
        "The archive contains all tracked project source at this revision, current test reports, "
        "and the headless Playwright visual-QA evidence. It does not claim production or mechanical "
        "qualification. See docs/phase4/final/LIMITATIONS.md.\n"
    ).encode()
    manifest = {
        "source_branch": branch,
        "source_revision": revision,
        "phase3_base_revision": BASE,
        "manifest_scope": "All members except this manifest",
        "files": [],
    }
    for name, path in sorted(files.items()):
        size, digest = sha256_path(path)
        manifest["files"].append({"path": name, "size_bytes": size, "sha256": digest})
    manifest["files"].extend(
        [
            {
                "path": f"{PREFIX}/SOURCE_README.txt",
                "size_bytes": len(readme),
                "sha256": hashlib.sha256(readme).hexdigest(),
            },
        ]
    )
    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", allowZip64=True) as archive:
        for name, path in sorted(files.items()):
            compression = (
                zipfile.ZIP_STORED
                if path.suffix.lower() in COMPRESSED_SUFFIXES
                else zipfile.ZIP_DEFLATED
            )
            archive.write(path, arcname=name, compress_type=compression)
        archive.writestr(f"{PREFIX}/SOURCE_README.txt", readme)
        archive.writestr(f"{PREFIX}/SOURCE_MANIFEST.json", manifest_bytes)

    expected = {row["path"]: row for row in manifest["files"]}
    with zipfile.ZipFile(OUTPUT) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Source archive CRC validation failed")
        names = set(archive.namelist())
        manifest_name = f"{PREFIX}/SOURCE_MANIFEST.json"
        if names != set(expected) | {manifest_name}:
            raise RuntimeError("Source archive member set differs from its manifest")
        for name, row in expected.items():
            with archive.open(name) as stream:
                size, digest = sha256_stream(stream)
            if size != row["size_bytes"] or digest != row["sha256"]:
                raise RuntimeError(
                    f"Source archive SHA-256 verification failed: {name}"
                )
        archived_manifest = json.loads(archive.read(manifest_name))
        if archived_manifest["source_revision"] != revision:
            raise RuntimeError("Source archive revision does not match Git HEAD")
    size, digest = sha256_path(OUTPUT)
    if size >= SIZE_LIMIT:
        raise RuntimeError(f"Source archive must be below 512 MB: {size:,} bytes")
    sidecar = OUTPUT.with_suffix(".sha256")
    sidecar.write_text(f"{digest}  {OUTPUT.name}  ({size} bytes)\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "archive": str(OUTPUT),
                "source_branch": branch,
                "source_revision": revision,
                "files_verified": len(expected),
                "archive_bytes": size,
                "archive_sha256": digest,
                "sha256_file": str(sidecar),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
