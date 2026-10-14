#!/usr/bin/env python3
"""Build small, native-frame comparison GLBs; never fabrication geometry.

VTK quadric decimation is optional. Originals remain unchanged. Each source node,
material color, byte fingerprint and sampled surface-error observation is retained.
Error samples are not landmark qualification or a global Hausdorff guarantee.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from phy_ref.catalog import load, verify_file
from phy_ref.glb import file_hash, open_glb

RECIPES = {"NIH_3DPX_020984": ("pelvis-preview.glb", 20000),
           "NIH_3DPX_020986": ("skin-preview.glb", 25000)}


def polydata(points, faces):
    import numpy as np
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
    p = vtk.vtkPoints();p.SetData(numpy_to_vtk(np.asarray(points, dtype=np.float64), deep=True))
    cells = vtk.vtkCellArray()
    packed = np.column_stack((np.full(len(faces), 3, dtype=np.int64), faces)).ravel()
    cells.SetCells(len(faces), numpy_to_vtkIdTypeArray(packed.astype(np.int64), deep=True))
    out = vtk.vtkPolyData();out.SetPoints(p);out.SetPolys(cells)
    return out


def arrays(poly):
    import numpy as np
    from vtk.util.numpy_support import vtk_to_numpy
    points = np.array(vtk_to_numpy(poly.GetPoints().GetData()), dtype=np.float32, copy=True)
    cells = np.array(vtk_to_numpy(poly.GetPolys().GetData()), dtype=np.int64, copy=True).reshape(-1, 4)
    if not np.all(cells[:, 0] == 3):
        raise ValueError("Preview produced non-triangle cells")
    return points, cells[:, 1:].astype(np.uint32)


def surface_error(source, target, samples):
    import vtk
    locator = vtk.vtkStaticCellLocator();locator.SetDataSet(target);locator.BuildLocator()
    cell, sub, distance = vtk.reference(0), vtk.reference(0), vtk.reference(0.)
    closest = [0., 0., 0.]
    maximum = 0.
    count = source.GetNumberOfPoints()
    step = max(1, math.ceil(count/samples))
    chosen = list(range(0, count, step))
    if chosen[-1] != count-1:
        chosen.append(count-1)
    for i in chosen:
        locator.FindClosestPoint(source.GetPoint(i), closest, cell, sub, distance)
        maximum = max(maximum, math.sqrt(float(distance)))
    return {"samples": len(chosen), "max_distance_mm": round(maximum*1000, 6)}


def write_glb(parts, path, asset):
    import numpy as np
    blob = bytearray()
    views, accessors, meshes, nodes, materials = [], [], [], [], []
    def accessor(values, typ, component):
        values = np.ascontiguousarray(values)
        blob.extend(b"\0" * (-len(blob) % 4))
        offset = len(blob);raw = values.tobytes(order="C");blob.extend(raw)
        vi = len(views);views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(raw)})
        row = {"bufferView": vi, "componentType": component, "count": len(values), "type": typ}
        if typ == "VEC3":
            row["min"] = [float(v) for v in values.min(axis=0)]
            row["max"] = [float(v) for v in values.max(axis=0)]
        ai = len(accessors);accessors.append(row);return ai
    for part in parts:
        pi = accessor(part["points"].astype("<f4"), "VEC3", 5126)
        ii = accessor(part["faces"].ravel().astype("<u4"), "SCALAR", 5125)
        rgba = part["rgba"]
        materials.append({"name": part["name"]+"_source_color",
                          "pbrMetallicRoughness": {"baseColorFactor": rgba, "metallicFactor": 0, "roughnessFactor": 1},
                          "doubleSided": True, **({"alphaMode": "BLEND"} if rgba[3] < 1 else {})})
        meshes.append({"name": part["name"], "primitives": [{"attributes": {"POSITION": pi}, "indices": ii,
                                                          "material": len(materials)-1, "mode": 4}]})
        nodes.append({"name": part["name"], "mesh": len(meshes)-1,
                      "extras": {"source_node": part["source_node"], "source_sha256": asset["sha256"],
                                 "status": "decimated_native_frame_display_only"}})
    doc = {"asset": {"version": "2.0", "generator": "PHY-REF native-frame preview / VTK 9.3.1",
                     "copyright": asset["attribution"]+"; CC BY 4.0; modified by decimation"},
           "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes, "meshes": meshes,
           "materials": materials, "buffers": [{"byteLength": len(blob)}], "bufferViews": views, "accessors": accessors,
           "extras": {"source_asset": asset["asset_id"], "source_sha256": asset["sha256"],
                      "anatomical_registration": None, "fabrication_released": False}}
    raw = (json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False)).encode()
    raw += b" " * (-len(raw) % 4);blob.extend(b"\0" * (-len(blob) % 4))
    content = (struct.pack("<4sII", b"glTF", 2, 28+len(raw)+len(blob))
               + struct.pack("<II", len(raw), 0x4E4F534A)+raw
               + struct.pack("<II", len(blob), 0x004E4942)+blob)
    Path(path).write_bytes(content)


def build(root, asset, output, budget):
    import numpy as np
    import vtk
    if type(budget) is not int or budget < 100:
        raise ValueError("Invalid preview triangle budget")
    if vtk.vtkVersion.GetVTKVersion() != "9.3.1":
        raise ValueError("Use pinned VTK 9.3.1 to reproduce this review recipe")
    source = verify_file(root, asset)
    parts, observations = [], []
    with open_glb(source) as model:
        checked = model.inspect()
        total = checked["scene_triangles"]
        for node in checked["nodes"]:
            if node["mesh"] is None or not node["in_default_scene"]:
                continue
            mesh = model.doc["meshes"][node["mesh"]]
            for ordinal, prim in enumerate(mesh["primitives"]):
                _, _, get_points = model.accessor(prim["attributes"]["POSITION"])
                points = np.asarray(list(get_points()), dtype=np.float64)
                if "indices" in prim:
                    _, _, get_indices = model.accessor(prim["indices"])
                    faces = np.fromiter((i[0] for i in get_indices()), dtype=np.uint32).reshape(-1, 3)
                else:
                    faces = np.arange(len(points), dtype=np.uint32).reshape(-1, 3)
                m = np.asarray(node["world_matrix"])
                points = points @ m[:3, :3].T + m[:3, 3]
                original = polydata(points, faces)
                clean = vtk.vtkCleanPolyData();clean.SetInputData(original);clean.SetTolerance(0);clean.Update()
                cleaned = clean.GetOutput()
                target = min(len(faces), max(50, math.floor(budget*len(faces)/total)))
                decimator = vtk.vtkQuadricDecimation();decimator.SetInputData(cleaned)
                decimator.SetTargetReduction(1-target/len(faces));decimator.VolumePreservationOn()
                decimator.Update();simplified = decimator.GetOutput()
                new_points, new_faces = arrays(simplified)
                if not len(new_faces) or not np.isfinite(new_points).all() or new_faces.max() >= len(new_points):
                    raise ValueError("Invalid decimated geometry")
                name = node["name"] if len(mesh["primitives"]) == 1 else str(node["name"])+"_"+str(ordinal)
                mat = model.doc.get("materials", [])[prim["material"]] if "material" in prim else {}
                rgba = mat.get("pbrMetallicRoughness", {}).get("baseColorFactor", [0.8, 0.8, 0.8, 1])
                parts.append({"name": name, "source_node": node["index"], "points": new_points,
                              "faces": new_faces, "rgba": rgba})
                observations.append({"name": name, "source_node": node["index"],
                                     "source_triangles": len(faces), "preview_triangles": len(new_faces),
                                     "source_bounds_m": {"min": points.min(axis=0).tolist(), "max": points.max(axis=0).tolist()},
                                     "preview_bounds_m": {"min": new_points.min(axis=0).tolist(), "max": new_points.max(axis=0).tolist()},
                                     "sampled_preview_to_source": surface_error(simplified, original, 4096),
                                     "sampled_source_to_preview": surface_error(original, simplified, 4096)})
    output = Path(output);output.parent.mkdir(parents=True, exist_ok=True)
    write_glb(parts, output, asset)
    with open_glb(output) as result:
        checked = result.inspect()
    if checked["scene_triangles"] > budget or output.stat().st_size > 5*1024*1024:
        output.unlink()
        raise ValueError("Preview exceeds triangle/byte budget")
    return {"asset_id": asset["asset_id"], "source_sha256": asset["sha256"],
            "preview_filename": output.name, "preview_sha256": file_hash(output),
            "preview_bytes": output.stat().st_size, "preview_triangles": checked["scene_triangles"],
            "triangle_budget": budget, "linear_units": "m", "coordinate_frame": "source world Y-up, unchanged",
            "recipe": "exact point weld; VTK quadric decimation with volume preservation; no registration/rescaling",
            "vtk_version": vtk.vtkVersion.GetVTKVersion(), "numpy_version": np.__version__,
            "tool_sha256": file_hash(Path(__file__)), "nodes": observations,
            "qualification": "display-only; samples are not a global error bound or landmark qualification",
            "fabrication_released": False, "canonical_transform": None,
            "normals": "omitted; viewer may calculate them", "textures_and_vertex_colors": "not retained; material base color retained"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT/"assets/nih/derived")
    args = parser.parse_args()
    results = []
    for asset in load(args.root/"sources/reference_assets.json")["assets"]:
        if asset["asset_id"] not in RECIPES:
            continue
        name, budget = RECIPES[asset["asset_id"]]
        results.append(build(args.root, asset, args.output/name, budget))
        print(name, results[-1]["preview_triangles"], results[-1]["preview_bytes"], flush=True)
    (args.output/"derivative_manifest.json").write_text(json.dumps(
        {"version": "1.0.0", "fabrication_released": False, "derivatives": results},
        indent=2, sort_keys=True, allow_nan=False)+"\n")


if __name__ == "__main__":
    main()
