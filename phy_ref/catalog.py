"""Admission metadata and integrity checks for explicitly selected assets."""
from __future__ import annotations
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit
from .glb import MAX_BYTES, file_hash, strict_json


def local_path(root, relative):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("Invalid asset path")
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("Asset path must remain within the repository")
    root = Path(root).resolve()
    result = (root/p).resolve()
    if not result.is_relative_to(root):
        raise ValueError("Asset path escapes repository")
    return result


def validate(catalog):
    if (not isinstance(catalog, dict) or catalog.get("catalog_version") != "1.0.0"
            or catalog.get("canon_effect") != "none" or catalog.get("fabrication_released") is not False):
        raise ValueError("Unsupported catalog or qualification claim")
    assets = catalog.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("Empty asset catalog")
    ids, paths = set(), set()
    for a in assets:
        if not isinstance(a, dict):
            raise ValueError("Asset must be an object")
        ident, path = a.get("asset_id"), a.get("path")
        if not isinstance(ident, str) or not re.fullmatch(r"NIH_3DPX_[0-9]{6}", ident) or ident in ids:
            raise ValueError("Invalid or duplicate asset ID")
        ids.add(ident)
        local_path(Path.cwd(), path)
        if path in paths or not path.endswith(".glb"):
            raise ValueError("Duplicate or non-GLB path")
        paths.add(path)
        for key in ("title", "original_filename", "reference_object_version", "attribution"):
            if not isinstance(a.get(key), str) or not a[key].strip():
                raise ValueError("Missing " + key + ": " + ident)
        if Path(path).name != a["original_filename"]:
            raise ValueError("Original filename must be preserved")
        size = a.get("bytes")
        if type(size) is not int or not 20 <= size <= MAX_BYTES:
            raise ValueError("Invalid asset byte count")
        if not isinstance(a.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", a["sha256"]):
            raise ValueError("Invalid SHA-256")
        if (a.get("license") != "CC-BY-4.0"
                or a.get("license_url") != "https://creativecommons.org/licenses/by/4.0/"
                or a.get("license_evidence") != "NIH entry metadata and rendered CC-BY-4.0 hyperlink"):
            raise ValueError("Missing reviewed rights evidence")
        u = urlsplit(a.get("download_url", ""))
        q = parse_qs(u.query)
        if (u.scheme != "https" or u.netloc != "3d.nih.gov" or u.path != "/api/download"
                or set(q) != {"submissionId", "fileIds"}
                or q["submissionId"] != [str(a.get("submission_id"))]
                or q["fileIds"] != [str(a.get("file_id"))]):
            raise ValueError("Download locator differs from selected NIH file")
        for key in ("submission_id", "file_id", "entry_version"):
            if type(a.get(key)) is not int or a[key] <= 0:
                raise ValueError("Invalid NIH identifier/version")
        if a.get("entry_url") != "https://3d.nih.gov/entries/3DPX-" + ident[-6:]:
            raise ValueError("Entry locator/identity mismatch")
        if (a.get("disposition") != "archived_reference_unregistered"
                or a.get("anatomically_qualified") is not False
                or a.get("fabrication_released") is not False
                or a.get("canonical_transform") is not None):
            raise ValueError("Unreviewed anatomical/canonical/fabrication promotion")
    return assets


def load(path):
    data = strict_json(Path(path).read_text())
    validate(data)
    return data


def verify_file(root, asset):
    path = local_path(root, asset["path"])
    if not path.is_file() or path.stat().st_size != asset["bytes"]:
        raise ValueError("Missing, LFS pointer or wrong-size asset: " + asset["asset_id"])
    digest = file_hash(path)
    if digest != asset["sha256"]:
        raise ValueError("Asset checksum mismatch: " + asset["asset_id"])
    return path
