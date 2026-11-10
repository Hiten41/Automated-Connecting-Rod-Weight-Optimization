from __future__ import annotations
import hashlib,json,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'
EXPECTED={
 'RodLab-Phase4-Solver-Evidence-Part-01-of-05.zip':('6945dc9d45783af3c97cf2df1d1062c9f4e5587442575748153a09658af0f3d9',361281497),
 'RodLab-Phase4-Solver-Evidence-Part-02-of-05.zip':('bc1e95dca051d36985268ebbf180c7f68f48cf18e7322d1c4fbe1d39879160dd',361281189),
 'RodLab-Phase4-Solver-Evidence-Part-03-of-05.zip':('ebed61193b2e72c54bdca9e0ed695276b35122bde0d860ad5bc7681c3e97c719',361280842),
 'RodLab-Phase4-Solver-Evidence-Part-04-of-05.zip':('84333d1f6b9097a1fd2be970a23c2aa2845ef0fedd98f82cfd56588bafc770de',361282024),
 'RodLab-Phase4-Solver-Evidence-Part-05-of-05.zip':('1ef21c849aaa56ef6af1839d54f80c47e6d71e5111e8a4c1c68cc063e338cd5b',361281071),
}

def hash_stream(stream):
 h=hashlib.sha256();size=0
 for block in iter(lambda:stream.read(1024*1024),b''):
  h.update(block);size+=len(block)
 return size,h.hexdigest()
def hash_file(path):
 with path.open('rb') as f:return hash_stream(f)

def verify_member(archive,name,size,digest):
 with archive.open(name) as f: actual_size,actual_hash=hash_stream(f)
 if actual_size!=size or actual_hash!=digest:
  raise RuntimeError(f'member verification failed: {name}')
 return actual_size,actual_hash

original_path=OUT/'phase4-final-solver-evidence.zip'
original_size,original_sha=hash_file(original_path)
with zipfile.ZipFile(original_path) as original:
 original_manifest_bytes=original.read('evidence_manifest.json')
 original_manifest=json.loads(original_manifest_bytes)
 if original_manifest.get('source_revision')!='dd86225d4465b759dc273ed8aa81e1cb283d15d4':raise RuntimeError('unexpected original evidence source revision')
 original_files={entry['path']:entry for entry in original_manifest['files']}
 if len(original_files)!=2262:raise RuntimeError('original evidence manifest does not contain 2,262 unique files')
 if len(original.namelist())!=2263 or set(original.namelist())!=set(original_files)|{'evidence_manifest.json'}:raise RuntimeError('original evidence archive membership mismatch')
 for i,(name,entry) in enumerate(sorted(original_files.items()),1):
  verify_member(original,name,entry['size_bytes'],entry['sha256'])
  if i%500==0:print(f'Verified original evidence {i}/2262',flush=True)
original_manifest_sha=hashlib.sha256(original_manifest_bytes).hexdigest()

parts=[];combined={}
for part_number in range(1,6):
 name=f'RodLab-Phase4-Solver-Evidence-Part-{part_number:02d}-of-05.zip'
 path=OUT/name;expected_sha,expected_size=EXPECTED[name]
 size,digest=hash_file(path)
 if size!=expected_size or digest!=expected_sha:raise RuntimeError(f'part file SHA/size differs from submitted checksum: {name}')
 with zipfile.ZipFile(path) as archive:
  split_meta_name=f'__split__/part-{part_number:02d}-manifest.json'
  part_meta=json.loads(archive.read(split_meta_name))
  if part_meta.get('part_index')!=part_number or part_meta.get('part_count')!=5:raise RuntimeError(f'part structure mismatch: {name}')
  if part_meta.get('source_revision')!=original_manifest['source_revision']:raise RuntimeError(f'source revision mismatch: {name}')
  if part_meta.get('source_evidence_archive_sha256')!=original_sha:raise RuntimeError(f'part does not identify the preserved original: {name}')
  if part_meta.get('source_evidence_manifest_sha256')!=original_manifest_sha:raise RuntimeError(f'original manifest hash mismatch: {name}')
  listed={entry['path']:entry for entry in part_meta['part_members']}
  if len(listed)!=len(part_meta['part_members']):raise RuntimeError(f'duplicate original paths in {name}')
  metadata_names={split_meta_name}
  if part_number==1:metadata_names.add('__split__/README.txt')
  if set(archive.namelist())!=set(listed)|metadata_names:raise RuntimeError(f'ZIP entries do not match per-part manifest: {name}')
  for source_name,entry in listed.items():
   if source_name in combined:raise RuntimeError(f'duplicate source path across split archives: {source_name}')
   if source_name!='evidence_manifest.json' and source_name not in original_files:raise RuntimeError(f'unexpected source path: {source_name}')
   verify_member(archive,source_name,entry['size_bytes'],entry['sha256'])
   if source_name!='evidence_manifest.json':
    source_entry=original_files[source_name]
    if (entry['size_bytes'],entry['sha256'])!=(source_entry['size_bytes'],source_entry['sha256']):raise RuntimeError(f'split part differs from original manifest: {source_name}')
   combined[source_name]=entry['sha256']
  if part_number==1:
   if listed.get('evidence_manifest.json',{}).get('sha256')!=original_manifest_sha:raise RuntimeError('original manifest is not preserved in part 1')
 parts.append({'filename':name,'size_bytes':size,'sha256':digest,'zip_entries':len(archive.namelist()),'original_evidence_entries':len(listed)})
if set(combined)!=set(original_files)|{'evidence_manifest.json'}:raise RuntimeError('the five parts do not reconstruct the original full manifest membership')

core_path=OUT/'RodLab-Phase4-Core-Deliverables-under512MB.zip'
core_size,core_sha=hash_file(core_path)
with zipfile.ZipFile(core_path) as core:
 if core.testzip() is not None:raise RuntimeError('core review ZIP CRC failure')
 core_manifest=json.loads(core.read('bundle-manifest.json'))
 if core_manifest.get('source_revision')!=original_manifest['source_revision']:raise RuntimeError('core and solver source revisions differ')
 if len(core_manifest.get('external_archives',[]))!=5:raise RuntimeError('core package does not identify all five evidence parts')

sidecar=OUT/'RodLab-Phase4-Solver-Evidence-PARTS-SHA256.txt'
sidecar_actual={line.split('  ',1)[1].split('  ',1)[0]:line.split('  ',1)[0] for line in sidecar.read_text(encoding='utf-8').splitlines()}
if any(sidecar_actual.get(p['filename'])!=p['sha256'] for p in parts):raise RuntimeError('parts SHA256SUMS content mismatch')
report={
 'verified_at_utc':datetime.now(timezone.utc).isoformat(),
 'repository_branch':'feature/phase4-physics-guided-redesign',
 'source_revision':original_manifest['source_revision'],
 'attachment_intake':'Named ZIP uploads were not present as separate files under the local Codex attachment cache. Existing local outputs were inspected; all five part hashes and sizes match the values in the supplied review brief.',
 'preserved_original_archive':{'path':'outputs/phase4-final-solver-evidence.zip','size_bytes':original_size,'sha256':original_sha,'zip_entries':2263,'manifest_file_count':2262,'integrity':'PASS','all_member_sizes_and_sha256':'PASS'},
 'split_archives':parts,
 'split_structure':'Five independent, valid ZIP archives; not split ZIP volumes and not concatenation fragments.',
 'combined_member_count':len(combined),
 'missing_members':[],
 'duplicate_source_paths':[],
 'unexpected_source_paths':[],
 'original_evidence_manifest_sha256':original_manifest_sha,
 'core_review_archive':{'path':'outputs/RodLab-Phase4-Core-Deliverables-under512MB.zip','size_bytes':core_size,'sha256':core_sha,'zip_entries':len(core.namelist()),'source_revision':core_manifest['source_revision'],'integrity':'PASS'},
 'known_scope_limit':'The evidence package validates stored CAD/FEA artifacts and their recorded provenance. It does not independently validate the physical model or establish mechanical qualification.',
}
(OUT/'phase4-evidence-intake.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
lines=[
 '# Phase 4 evidence intake report','',
 '## Repository and intake','','- Branch: `feature/phase4-physics-guided-redesign`','- Source revision represented by both source and evidence packages: `dd86225d4465b759dc273ed8aa81e1cb283d15d4`','- The attachment cache did not contain separate files with the submitted ZIP filenames. The project-local copies under `outputs/` were inspected; all five part sizes and SHA-256 values match the values in the supplied review brief.','- The original local evidence archive was retained unchanged at `outputs/phase4-final-solver-evidence.zip`.','',
 '## Preserved original solver evidence','','- ZIP integrity: PASS (every listed member was read to EOF, validating CRC).','- ZIP entries: 2,263 (2,262 evidence files plus `evidence_manifest.json`).','- Original manifest source revision: `'+original_manifest['source_revision']+'`.','- Original evidence manifest SHA-256: `'+original_manifest_sha+'`.','- Original archive size: '+str(original_size)+' bytes.','- Original archive SHA-256: `'+original_sha+'`.','- Every original manifest entry path, byte size and SHA-256 was checked against the archive contents.','',
 '## Five submitted evidence parts','','Each part opens as an independent ZIP archive. They are not multipart ZIP volumes and must not be concatenated. Each part contains a `__split__/part-NN-of-05-manifest.json` listing the original paths and hashes it carries. Part 01 contains the original `evidence_manifest.json`. Extract all five into one destination folder to reconstruct the original artifact tree.','',
 '| Part | Bytes | ZIP entries | Original evidence entries | SHA-256 |','|---|---:|---:|---:|---|'
]
for p in parts:lines.append(f"| `{p['filename']}` | {p['size_bytes']} | {p['zip_entries']} | {p['original_evidence_entries']} | `{p['sha256']}` |")
lines += ['', 'Combined original evidence members verified: **2,262**; missing: **0**; duplicate source paths: **0**; unexpected source paths: **0**.', '', '## Core review package', '', f"- Path: `outputs/{core_path.name}`", f'- Size: {core_size} bytes.', f'- SHA-256: `{core_sha}`.', f'- ZIP entries: {len(core.namelist())}.', '- Core manifest source revision matches the original solver evidence and identifies all five evidence parts.', '', '## Limits', '', 'This intake verifies archive integrity, membership, sizes, hashes and recorded source revision. It does not claim that a separate ChatGPT reviewer has inspected the package, does not independently rerun the solver, and does not establish production or mechanical qualification.', '']
(ROOT/'docs/phase4/final/EVIDENCE_INTAKE_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'report':'docs/phase4/final/EVIDENCE_INTAKE_REPORT.md','json':'outputs/phase4-evidence-intake.json','original_files_verified':len(original_files),'split_parts':len(parts),'core_bytes':core_size,'original_archive_sha256':original_sha},indent=2))