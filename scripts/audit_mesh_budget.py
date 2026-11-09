import json
from conrod.fea import ROOT

r = ROOT
rows = []
for folder in (r / "runs/phase2-experiments").iterdir():
    if not folder.is_dir() or not (folder / "result.json").exists():
        continue
    d = json.loads((folder / "result.json").read_text())
    if d["status"] == "FEA_SUCCESS":
        continue
    mesh = folder / "mesh.msh"
    n = None
    if mesh.exists():
        with mesh.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip() == "$Nodes":
                    n = int(next(f).split()[1])
                    break
    q = (
        json.loads((folder / "mesh-quality.json").read_text())
        if (folder / "mesh-quality.json").exists()
        else {}
    )
    rows.append(
        dict(
            case=folder.name,
            node_count=n,
            element_count=q.get("element_count"),
            mesh_quality=q,
            runtime_s=d.get("runtime_s"),
            status=d["status"],
            error=d.get("error"),
        )
    )
(r / "evidence/phase2/mesh-budget-audit.json").write_text(json.dumps(rows, indent=2))
print([(x["case"], x["node_count"], x["element_count"]) for x in rows])
