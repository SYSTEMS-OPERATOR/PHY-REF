#!/usr/bin/env python3
"""Audit verified static NIH GLBs offline; qualification remains open."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from phy_ref.catalog import load, verify_file
from phy_ref.glb import open_glb


def audit(root):
    catalog = load(root/"sources/reference_assets.json")
    reports = {}
    for asset in catalog["assets"]:
        path = verify_file(root, asset)
        with open_glb(path) as model:
            result = model.inspect()
        result.update(asset_id=asset["asset_id"], path=asset["path"], sha256=asset["sha256"],
                      bytes=asset["bytes"], entry_version=asset["entry_version"],
                      reference_object_version=asset["reference_object_version"])
        reports[asset["original_filename"].removesuffix(".glb")+".json"] = result
    return catalog, reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT/"reports/mesh_audits")
    args = parser.parse_args()
    try:
        catalog, reports = audit(args.root)
        # Check all inputs before replacing any observation.
        args.output.mkdir(parents=True, exist_ok=True)
        encoded = {name: (json.dumps(report, indent=2, sort_keys=True, allow_nan=False)+"\n").encode()
                   for name, report in reports.items()}
        manifest = {"version": "1.0.0", "fabrication_released": False,
                    "catalog_sha256": hashlib.sha256((args.root/"sources/reference_assets.json").read_bytes()).hexdigest(),
                    "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in encoded.items()}}
        encoded["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True)+"\n").encode()
        with tempfile.TemporaryDirectory(dir=args.output) as temp:
            for name, raw in encoded.items():
                (Path(temp)/name).write_bytes(raw)
            for name in encoded:
                (Path(temp)/name).replace(args.output/name)
        for name, report in reports.items():
            print(json.dumps({"asset": report["asset_id"], "meshes": report["unique_mesh_count"],
                              "scene_triangles": report["scene_triangles"], "fabrication_released": False}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as error:
        print(json.dumps({"completed": False, "issue": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
