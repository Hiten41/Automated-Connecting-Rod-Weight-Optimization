"""Verify the Phase 4 source, evidence, test and UI release deliverables."""

from __future__ import annotations

import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from package_phase4_evidence import verify_archive

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/phase4-final-release-manifest.json"
SOURCE_ZIP = (
    ROOT / "outputs/phase4-complete-review-bundle/rodLab-phase4-complete-source.zip"
)
EVIDENCE_ZIP = ROOT / "outputs/phase4-final-solver-evidence-final.zip"
PART_PATTERN = "RodLab-Phase4-Final-Solver-Evidence-Part-*-of-05.zip"
QA_DIR = ROOT / "outputs/phase4-visual-qa"
BASE = "0981e89f8189814041813b26d9dd4c2f1cd35ef1"
PART_SIZE_LIMIT = 512_000_000


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def hash_stream(stream) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        size += len(block)
        digest.update(block)
    return size, digest.hexdigest()


def hash_file(path: Path) -> tuple[int, str]:
    with path.open("rb") as stream:
        return hash_stream(stream)


def verify_source_zip(path: Path, revision: str) -> dict:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Source ZIP CRC check failed")
        manifest_name = "rodLab-phase4/SOURCE_MANIFEST.json"
        manifest = json.loads(archive.read(manifest_name))
        if manifest.get("source_revision") != revision:
            raise RuntimeError("Source ZIP identifies a different Git revision")
        entries = {row["path"]: row for row in manifest["files"]}
        if set(archive.namelist()) != set(entries) | {manifest_name}:
            raise RuntimeError("Source ZIP member list differs from its manifest")
        for name, entry in entries.items():
            with archive.open(name) as stream:
                size, digest = hash_stream(stream)
            if size != entry["size_bytes"] or digest != entry["sha256"]:
                raise RuntimeError(f"Source ZIP member hash mismatch: {name}")
    size, digest = hash_file(path)
    if size >= PART_SIZE_LIMIT:
        raise RuntimeError("Source ZIP is not below 512 MB")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "size_bytes": size,
        "sha256": digest,
        "verified_members": len(entries),
    }


def junit_counts(path: Path) -> dict:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    return {
        key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }


def verify_parts(revision: str, evidence_manifest: dict) -> list[dict]:
    expected = {row["path"]: row for row in evidence_manifest["files"]}
    source_names = set(expected) | {"evidence_manifest.json"}
    observed = {}
    parts = sorted((ROOT / "outputs").glob(PART_PATTERN))
    if len(parts) != 5:
        raise RuntimeError(f"Expected 5 final evidence parts, found {len(parts)}")
    records = []
    for index, path in enumerate(parts, start=1):
        size, digest = hash_file(path)
        if size >= PART_SIZE_LIMIT:
            raise RuntimeError(f"Evidence part is not below 512 MB: {path.name}")
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise RuntimeError(f"Evidence ZIP CRC check failed: {path.name}")
            meta = json.loads(archive.read(f"__split__/part-{index:02d}-manifest.json"))
            if (
                meta.get("source_revision") != revision
                or meta.get("part_index") != index
            ):
                raise RuntimeError(
                    f"Evidence part revision/index mismatch: {path.name}"
                )
            for entry in meta["part_members"]:
                name = entry["path"]
                if name in observed:
                    raise RuntimeError(f"Duplicate path across evidence parts: {name}")
                with archive.open(name) as stream:
                    member_size, member_digest = hash_stream(stream)
                if (
                    member_size != entry["size_bytes"]
                    or member_digest != entry["sha256"]
                ):
                    raise RuntimeError(f"Part member hash mismatch: {path.name}:{name}")
                if name == "evidence_manifest.json":
                    with zipfile.ZipFile(EVIDENCE_ZIP) as source:
                        expected_digest = hashlib.sha256(
                            source.read("evidence_manifest.json")
                        ).hexdigest()
                    if member_digest != expected_digest:
                        raise RuntimeError(
                            "Evidence part includes a mismatched manifest"
                        )
                elif (
                    name not in expected
                    or member_size != expected[name]["size_bytes"]
                    or member_digest != expected[name]["sha256"]
                ):
                    raise RuntimeError(
                        f"Part member differs from evidence manifest: {name}"
                    )
                observed[name] = member_digest
        records.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": size,
                "sha256": digest,
                "verified_members": len(meta["part_members"]),
            }
        )
    if set(observed) != source_names:
        raise RuntimeError(
            "Evidence parts do not cover every full-archive member exactly once"
        )
    return records


def main() -> None:
    branch = git("branch", "--show-current")
    revision = git("rev-parse", "HEAD")
    if branch != "feature/phase4-physics-guided-redesign":
        raise RuntimeError(f"Unexpected final source branch: {branch}")
    if git("merge-base", "--is-ancestor", BASE, "HEAD"):
        raise RuntimeError("Phase 3 base is not an ancestor of the final commit")
    if git("status", "--porcelain"):
        raise RuntimeError("Git worktree is not clean")

    source = verify_source_zip(SOURCE_ZIP, revision)
    evidence_result = verify_archive(EVIDENCE_ZIP, revision)
    with zipfile.ZipFile(EVIDENCE_ZIP) as archive:
        evidence_manifest = json.loads(archive.read("evidence_manifest.json"))
    evidence_size, evidence_digest = hash_file(EVIDENCE_ZIP)
    evidence = {
        "path": EVIDENCE_ZIP.relative_to(ROOT).as_posix(),
        "size_bytes": evidence_size,
        "sha256": evidence_digest,
        "verified_members": evidence_result["verified_files"],
        "manifest": "evidence_manifest.json",
    }
    parts = verify_parts(revision, evidence_manifest)

    full_tests = junit_counts(ROOT / "data/phase4/all-test-results.xml")
    integration_tests = junit_counts(ROOT / "data/phase4/integration-test-results.xml")
    unit_tests = junit_counts(ROOT / "data/phase4/unit-test-results.xml")
    for name, counts in (
        ("full", full_tests),
        ("integration", integration_tests),
        ("unit", unit_tests),
    ):
        if counts["failures"] or counts["errors"]:
            raise RuntimeError(f"{name} JUnit report contains test failures: {counts}")

    browser = json.loads(
        (QA_DIR / "browser-qa-report.json").read_text(encoding="utf-8")
    )
    if (
        len(browser.get("cases", [])) != 50
        or browser.get("browserIssues")
        or browser.get("dashboardRawJsonVisible")
    ):
        raise RuntimeError("Browser QA report does not show a clean 50-case run")
    actions_path = QA_DIR / "github-actions-status.json"
    refs_path = QA_DIR / "git-ref-audit.json"
    actions = json.loads(actions_path.read_text(encoding="utf-8"))
    refs = json.loads(refs_path.read_text(encoding="utf-8"))
    if (
        actions.get("conclusion") != "success"
        or refs.get("previous_branches_unchanged") is not True
    ):
        raise RuntimeError("GitHub Actions or branch-isolation audit did not pass")

    manifest = {
        "source_branch": branch,
        "source_revision": revision,
        "phase3_base_revision": BASE,
        "source_zip": source,
        "evidence_archive": evidence,
        "evidence_parts": parts,
        "part_size_limit_bytes": PART_SIZE_LIMIT,
        "test_reports": {
            "full": full_tests,
            "integration": integration_tests,
            "unit": unit_tests,
        },
        "browser_qa": {
            "report_path": "outputs/phase4-visual-qa/browser-qa-report.json",
            "report_sha256": browser.get("reportSha256"),
            "cases": len(browser["cases"]),
            "browser_issues": len(browser["browserIssues"]),
            "dashboard_raw_json_visible": browser["dashboardRawJsonVisible"],
        },
        "github_actions": actions,
        "git_ref_audit": refs,
        "mechanical_qualification": "NOT_QUALIFIED",
    }
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(OUTPUT), **manifest}, indent=2))


if __name__ == "__main__":
    main()
