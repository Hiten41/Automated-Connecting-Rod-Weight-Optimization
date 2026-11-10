"""Split the final Phase 4 evidence ZIP into verified sub-512 MB ZIP archives."""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/phase4-final-solver-evidence-final.zip"
OUTPUT = ROOT / "outputs"
PART_COUNT = 5
SIZE_LIMIT = 512_000_000


def digest_stream(stream, destination=None) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        size += len(block)
        digest.update(block)
        if destination is not None:
            destination.write(block)
    return size, digest.hexdigest()


def digest_file(path: Path) -> tuple[int, str]:
    with path.open("rb") as stream:
        return digest_stream(stream)


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def split_archive() -> dict:
    if not SOURCE.is_file():
        raise RuntimeError(f"Final evidence archive is missing: {SOURCE}")
    source_size, source_digest = digest_file(SOURCE)
    with zipfile.ZipFile(SOURCE) as source:
        source_manifest_bytes = source.read("evidence_manifest.json")
        source_manifest = json.loads(source_manifest_bytes)
        revision = source_manifest.get("source_revision")
        if revision != git_head():
            raise RuntimeError("Evidence revision does not match the current Git HEAD")
        expected = {row["path"]: row for row in source_manifest.get("files", [])}
        payload = [entry for entry in source.infolist() if not entry.is_dir()]
        expected_names = set(expected) | {"evidence_manifest.json"}
        if {entry.filename for entry in payload} != expected_names:
            raise RuntimeError("Evidence archive membership differs from its manifest")

        bins: list[list[zipfile.ZipInfo]] = [[] for _ in range(PART_COUNT)]
        loads = [0] * PART_COUNT
        for entry in sorted(payload, key=lambda row: row.compress_size, reverse=True):
            index = (
                0
                if entry.filename == "evidence_manifest.json"
                else min(range(PART_COUNT), key=lambda value: loads[value])
            )
            bins[index].append(entry)
            loads[index] += entry.compress_size

        index_data = {
            "format": "RodLab Phase 4 final solver evidence split archive",
            "source_revision": revision,
            "source_branch": source_manifest.get("source_branch"),
            "source_archive": SOURCE.name,
            "source_archive_size_bytes": source_size,
            "source_archive_sha256": source_digest,
            "source_manifest_sha256": hashlib.sha256(source_manifest_bytes).hexdigest(),
            "part_count": PART_COUNT,
            "reassembly": "Extract every part ZIP into the same empty folder. Original member paths are retained; the complete evidence_manifest.json is in part 01.",
        }
        parts = []
        for index, members in enumerate(bins, start=1):
            filename = f"RodLab-Phase4-Final-Solver-Evidence-Part-{index:02d}-of-{PART_COUNT:02d}.zip"
            destination = OUTPUT / filename
            part_members = []
            with zipfile.ZipFile(
                destination,
                "w",
                allowZip64=True,
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as target:
                for entry in sorted(members, key=lambda row: row.filename):
                    output_info = zipfile.ZipInfo(entry.filename, entry.date_time)
                    output_info.compress_type = entry.compress_type
                    output_info.external_attr = entry.external_attr
                    output_info.create_system = entry.create_system
                    with (
                        source.open(entry) as reader,
                        target.open(output_info, "w") as writer,
                    ):
                        size, digest = digest_stream(reader, writer)
                    if entry.filename == "evidence_manifest.json":
                        if digest != index_data["source_manifest_sha256"]:
                            raise RuntimeError(
                                "Embedded evidence manifest changed while splitting"
                            )
                    elif (
                        size != expected[entry.filename]["size_bytes"]
                        or digest != expected[entry.filename]["sha256"]
                    ):
                        raise RuntimeError(
                            f"Source artifact changed while splitting: {entry.filename}"
                        )
                    part_members.append(
                        {"path": entry.filename, "size_bytes": size, "sha256": digest}
                    )
                part_manifest = {
                    **index_data,
                    "part_index": index,
                    "part_filename": filename,
                    "part_member_count": len(part_members),
                    "part_members": part_members,
                }
                target.writestr(
                    f"__split__/part-{index:02d}-manifest.json",
                    json.dumps(part_manifest, indent=2).encode("utf-8"),
                )
                if index == 1:
                    target.writestr(
                        "__split__/README.txt",
                        (
                            "RodLab Phase 4 final evidence ZIP part 01\n\n"
                            f"Extract all {PART_COUNT} ZIP parts into the same empty folder. "
                            "The original evidence paths are preserved. The complete "
                            "evidence_manifest.json is in this part.\n\n"
                            f"Source revision: {revision}\n"
                        ).encode(),
                    )
            size = destination.stat().st_size
            if size >= SIZE_LIMIT:
                raise RuntimeError(f"{filename} is not below 512 MB: {size:,} bytes")
            parts.append(destination)
            print(f"Built {filename}: {size:,} bytes", flush=True)

        observed = {}
        for index, path in enumerate(parts, start=1):
            if path.stat().st_size >= SIZE_LIMIT:
                raise RuntimeError(f"Part exceeds the size limit: {path.name}")
            with zipfile.ZipFile(path) as archive:
                corrupt = archive.testzip()
                if corrupt:
                    raise RuntimeError(
                        f"ZIP CRC validation failed: {path.name}:{corrupt}"
                    )
                metadata = json.loads(
                    archive.read(f"__split__/part-{index:02d}-manifest.json")
                )
                if (
                    metadata["source_revision"] != revision
                    or metadata["part_count"] != PART_COUNT
                    or metadata["part_index"] != index
                ):
                    raise RuntimeError(f"Split metadata mismatch in {path.name}")
                for row in metadata["part_members"]:
                    name = row["path"]
                    if name in observed:
                        raise RuntimeError(f"Duplicate split member: {name}")
                    with archive.open(name) as stream:
                        size, digest = digest_stream(stream)
                    if size != row["size_bytes"] or digest != row["sha256"]:
                        raise RuntimeError(f"Part member verification failed: {name}")
                    if name == "evidence_manifest.json":
                        if digest != index_data["source_manifest_sha256"]:
                            raise RuntimeError(
                                "Wrong manifest was included in the parts"
                            )
                    elif (
                        size != expected[name]["size_bytes"]
                        or digest != expected[name]["sha256"]
                    ):
                        raise RuntimeError(f"Source manifest check failed: {name}")
                    observed[name] = digest
        if set(observed) != expected_names:
            raise RuntimeError(
                f"Split coverage mismatch: expected {len(expected_names)}, got {len(observed)}"
            )

    checksums = []
    records = []
    for path in parts:
        size, digest = digest_file(path)
        checksums.append(f"{digest}  {path.name}  ({size} bytes)")
        records.append({"path": str(path), "size_bytes": size, "sha256": digest})
    checksum_path = OUTPUT / "RodLab-Phase4-Final-Solver-Evidence-PARTS-SHA256.txt"
    checksum_path.write_text("\n".join(checksums) + "\n", encoding="utf-8")
    result = {
        "source_archive": str(SOURCE),
        "source_archive_sha256": source_digest,
        "source_revision": revision,
        "verified_source_members": len(expected),
        "manifest_included": True,
        "part_count": PART_COUNT,
        "size_limit_bytes": SIZE_LIMIT,
        "parts": records,
        "checksums": str(checksum_path),
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    split_archive()
