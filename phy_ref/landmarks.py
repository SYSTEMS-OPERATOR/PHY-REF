"""Custody and geometric checks for unaccepted pelvis preview annotations.

Reconstructing a point proves its relation to the pinned preview triangle only.
It does not identify an anatomical feature or qualify the original surface.
"""
from __future__ import annotations

import math
from pathlib import Path
import re

from .glb import file_hash, open_glb, point, strict_json
from .catalog import local_path

PACKET_PATH = "reviews/pelvis_left_landmarks.json"
IDS = {"L_ASIS", "L_PSIS", "L_PUBIC_TUBERCLE", "L_ISCHIAL_TUBEROSITY", "SACRAL_PROMONTORY"}


def load_packet(root):
    root = Path(root)
    packet = strict_json((root / PACKET_PATH).read_text())
    if (packet.get("schema_version") != "PHY_PELVIS_LANDMARK_REVIEW_V1"
            or packet.get("status") != "awaiting_independent_review"
            or packet.get("canonical_transform") is not None
            or packet.get("fabrication_released") is not False
            or packet.get("accepted_landmarks") is not None):
        raise ValueError("Unreviewed landmark promotion or unsupported packet")
    landmarks = packet.get("landmarks", [])
    if len(landmarks) != len(IDS) or {p.get("id") for p in landmarks} != IDS:
        raise ValueError("Landmark identity scope changed")
    for landmark in landmarks:
        if (landmark.get("accepted_native_point_m") is not None
                or landmark.get("anatomically_accepted") is not False
                or not landmark.get("definition") or not landmark.get("review_rule")
                or not landmark.get("preview_mesh_names")):
            raise ValueError("Missing definition or unreviewed anatomical coordinate")
    if (packet.get("units") != "m"
            or packet.get("coordinate_frame") != "source world Y-up, unchanged"):
        raise ValueError("Native frame/units changed")
    for path, digest in packet["custody_files"].items():
        if file_hash(local_path(root, path)) != digest:
            raise ValueError("Packet custody mismatch: " + path)
    catalog = strict_json((root / "sources/reference_assets.json").read_text())
    source = next(a for a in catalog["assets"] if a["asset_id"] == packet["source"]["asset_id"])
    for key in ("path", "sha256", "bytes", "entry_version", "reference_object_version"):
        if packet["source"][key] != source[key]:
            raise ValueError("Original source identity mismatch")
    preview = packet["preview"]
    path = local_path(root, preview["path"])
    if path.stat().st_size != preview["bytes"] or file_hash(path) != preview["sha256"]:
        raise ValueError("Preview custody mismatch")
    with open_glb(path) as glb:
        inspection = glb.inspect()
        names = {n["name"] for n in inspection["nodes"] if n["mesh"] is not None}
        for landmark in landmarks:
            if not set(landmark["preview_mesh_names"]).issubset(names):
                raise ValueError("Landmark source label absent")
    return packet


def validate_draft(root, draft):
    """Check a Studio draft against bytes; reject original/accepted claims."""
    root = Path(root)
    packet = load_packet(root)
    if (draft.get("kind") != "PHY_PELVIS_PREVIEW_DRAFT_V1"
            or draft.get("packet_id") != packet["packet_id"]
            or draft.get("packet_sha256") != file_hash(root / PACKET_PATH)
            or draft.get("source_sha256") != packet["source"]["sha256"]
            or draft.get("preview_sha256") != packet["preview"]["sha256"]
            or not re.fullmatch(r"[0-9a-f]{40}", draft.get("reference_revision", ""))
            or draft.get("canonical_transform") is not None
            or draft.get("fabrication_released") is not False
            or draft.get("accepted_landmarks") is not None):
        raise ValueError("Draft custody or qualification claim invalid")
    definitions = {p["id"]: p for p in packet["landmarks"]}
    annotations = draft.get("annotations")
    if not isinstance(annotations, list) or len(annotations) > len(IDS):
        raise ValueError("Invalid annotation list")
    seen = set()
    with open_glb(root / packet["preview"]["path"]) as glb:
        inspected = glb.inspect()
        nodes = {n["name"]: n for n in inspected["nodes"]}
        for a in annotations:
            ident = a.get("landmark_id")
            if ident not in definitions or ident in seen:
                raise ValueError("Unknown or duplicate landmark")
            seen.add(ident)
            if (a.get("anatomically_accepted") is not False
                    or a.get("original_face_index") is not None
                    or a.get("mesh_name") not in definitions[ident]["preview_mesh_names"]):
                raise ValueError("Wrong anatomical label or original/accepted claim")
            node = nodes[a["mesh_name"]]
            native = glb.doc["nodes"][node["index"]]
            if (a.get("preview_node") != node["index"]
                    or a.get("source_node") != native["extras"]["source_node"]):
                raise ValueError("Node lineage mismatch")
            prim = glb.doc["meshes"][node["mesh"]]["primitives"][0]
            _, _, positions = glb.accessor(prim["attributes"]["POSITION"])
            _, count, indices = glb.accessor(prim["indices"])
            face = a.get("face_index")
            if type(face) is not int or not 0 <= face < count // 3:
                raise ValueError("Face index outside preview")
            vertices = [v[0] for v in indices()][face * 3:face * 3 + 3]
            if a.get("vertex_indices") != vertices:
                raise ValueError("Triangle vertex lineage mismatch")
            weights = a.get("barycentric")
            xyz = a.get("native_point_m")
            for values in (weights, xyz):
                if (not isinstance(values, list) or len(values) != 3
                        or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
                    raise ValueError("Invalid finite annotation vector")
            if min(weights) < -1e-7 or max(weights) > 1 + 1e-7 or abs(sum(weights) - 1) > 1e-7:
                raise ValueError("Barycentric point outside triangle")
            points = list(positions())
            local = [sum(weights[j] * points[vertices[j]][i] for j in range(3)) for i in range(3)]
            actual = point(node["world_matrix"], local)
            if math.dist(actual, xyz) > 1e-7:
                raise ValueError("Native point does not reconstruct from preview triangle")
    return {"status": "preview_geometry_verified_only", "annotations": len(annotations),
            "anatomically_accepted": False, "fabrication_released": False}
