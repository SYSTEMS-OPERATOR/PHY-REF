#!/usr/bin/env python3
"""Explicitly acquire pinned public NIH originals, without source upgrades."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import sys
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from phy_ref.catalog import load, local_path, verify_file


def acquire(root, asset, opener=urllib.request.urlopen):
    dest = local_path(root, asset["path"])
    if dest.exists():
        try:
            verify_file(root, asset)
            return "already_verified"
        except ValueError:
            # An LFS checkout intentionally contains a pointer before hydration.
            if dest.stat().st_size > 1024 or not dest.read_bytes().startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                raise ValueError("Refusing to replace an existing non-pointer asset")
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as out:
            temp = Path(out.name)
            digest, size = hashlib.sha256(), 0
            request = urllib.request.Request(asset["download_url"], headers={"User-Agent": "PHY-REF-Reference-Archive/1.0"})
            with opener(request, timeout=60) as response:
                if urllib.parse.urlsplit(response.geturl()).hostname != "3d.nih.gov":
                    raise ValueError("Unexpected download response host")
                for chunk in iter(lambda: response.read(1024*1024), b""):
                    size += len(chunk)
                    if size > asset["bytes"]:
                        raise ValueError("NIH response exceeds expected original size")
                    digest.update(chunk)
                    out.write(chunk)
        if size != asset["bytes"] or digest.hexdigest() != asset["sha256"]:
            raise ValueError("NIH original size/hash differs from catalog")
        with temp.open("rb") as f:
            if f.read(4) != b"glTF":
                raise ValueError("Selected download is not a GLB")
        temp.replace(dest)
        return "downloaded_and_verified"
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="acquire only catalog originals")
    group.add_argument("--asset", help="one catalog asset ID")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    assets = load(args.root/"sources/reference_assets.json")["assets"]
    selected = assets if args.all else [a for a in assets if a["asset_id"] == args.asset]
    if not selected:
        parser.error("Unknown asset ID")
    for asset in selected:
        print(asset["asset_id"] + ": " + acquire(args.root, asset), flush=True)


if __name__ == "__main__":
    main()
