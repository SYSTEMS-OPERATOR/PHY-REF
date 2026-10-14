"""Bounded static GLB 2.0 inspection; no external buffers or mesh repair.

The checker supports FLOAT VEC3 positions, unsigned triangle indices and static
node transforms. Unsupported geometry fails explicitly rather than being
counted as inspected. It does not certify anatomy, watertightness or fabrication.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import itertools
import json
import math
import mmap
from pathlib import Path
import struct

MAX_BYTES = 256 * 1024 * 1024
IDENTITY = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def strict_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("Duplicate JSON field: " + k)
            result[k] = v
        return result
    def reject(value):
        raise ValueError("Nonfinite JSON value: " + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)


def natural(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("Invalid integer: " + label)
    return value


def finite(values, count, label):
    if (not isinstance(values, list) or len(values) != count
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
        raise ValueError("Invalid finite vector: " + label)
    return values


def product(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def node_matrix(node):
    if "matrix" in node:
        if any(k in node for k in ("translation", "rotation", "scale")):
            raise ValueError("Node mixes matrix and TRS")
        v = finite(node["matrix"], 16, "matrix")
        m = [[v[j * 4 + i] for j in range(4)] for i in range(4)]
        if m[3] != [0, 0, 0, 1]:
            raise ValueError("Non-affine node matrix")
        return m
    t = finite(node.get("translation", [0, 0, 0]), 3, "translation")
    s = finite(node.get("scale", [1, 1, 1]), 3, "scale")
    if any(x == 0 for x in s):
        raise ValueError("Singular node scale")
    x, y, z, w = finite(node.get("rotation", [0, 0, 0, 1]), 4, "quaternion")
    if not math.isclose(x*x + y*y + z*z + w*w, 1, abs_tol=1e-6):
        raise ValueError("Non-unit node quaternion")
    r = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
         [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
         [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    return [[r[i][j]*s[j] if j < 3 else t[i] for j in range(4)]
            for i in range(3)] + [[0, 0, 0, 1]]


def point(m, p):
    return [sum(m[i][j]*p[j] for j in range(3)) + m[i][3] for i in range(3)]


def transformed_box(bounds, m):
    corners = [point(m, p) for p in itertools.product(*zip(bounds["min"], bounds["max"]))]
    return {"min": [min(p[i] for p in corners) for i in range(3)],
            "max": [max(p[i] for p in corners) for i in range(3)]}


def union(boxes):
    if not boxes:
        return None
    return {"min": [min(b["min"][i] for b in boxes) for i in range(3)],
            "max": [max(b["max"][i] for b in boxes) for i in range(3)]}


class GLB:
    def __init__(self, raw):
        self.raw = raw
        if len(raw) < 20 or len(raw) > MAX_BYTES:
            raise ValueError("GLB size outside inspection budget")
        magic, version, length = struct.unpack_from("<4sII", raw)
        if magic != b"glTF" or version != 2 or length != len(raw):
            raise ValueError("Invalid GLB header or length; materialize LFS first")
        chunks = []
        offset = 12
        while offset < length:
            if offset + 8 > length:
                raise ValueError("Truncated chunk header")
            size, kind = struct.unpack_from("<II", raw, offset)
            start, end = offset+8, offset+8+size
            if size % 4 or end > length:
                raise ValueError("Truncated or unaligned GLB chunk")
            chunks.append((kind, start, end))
            offset = end
        if not chunks or chunks[0][0] != 0x4E4F534A:
            raise ValueError("First GLB chunk must be JSON")
        if len(chunks) != 2 or chunks[1][0] != 0x004E4942:
            raise ValueError("Expected one JSON and one BIN chunk")
        self.doc = strict_json(bytes(raw[chunks[0][1]:chunks[0][2]]))
        if not isinstance(self.doc, dict) or self.doc.get("asset", {}).get("version") != "2.0":
            raise ValueError("Unsupported glTF asset version")
        if self.doc.get("extensionsRequired"):
            raise ValueError("Required extensions are outside the inspection contract")
        if self.doc.get("skins") or self.doc.get("animations"):
            raise ValueError("Only static, unskinned assets are supported")
        self.bin_start, self.bin_end = chunks[1][1:]
        buffers = self.doc.get("buffers", [])
        if len(buffers) != 1 or buffers[0].get("uri") is not None:
            raise ValueError("Only the embedded GLB buffer is supported")
        self.bin_size = natural(buffers[0].get("byteLength"), "buffer length", 1)
        if not 0 <= self.bin_end-self.bin_start-self.bin_size <= 3:
            raise ValueError("BIN padding/length mismatch")
        self._bounds = {}
        self._counts = {}

    def accessor(self, index):
        index = natural(index, "accessor index")
        try:
            a = self.doc["accessors"][index]
            if a.get("sparse") or a.get("normalized") or a.get("extensions"):
                raise ValueError("Sparse, normalized or extended accessor unsupported")
            count = natural(a.get("count"), "accessor count", 1)
            v = self.doc["bufferViews"][natural(a["bufferView"], "bufferView index")]
            if v.get("buffer", 0) != 0 or v.get("extensions"):
                raise ValueError("Unsupported buffer view")
            formats = {5121: ("B", 1), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
            fmt, size = formats[a["componentType"]]
            widths = {"SCALAR": 1, "VEC3": 3}
            width = widths[a["type"]]
            item_size = width*size
            stride = natural(v.get("byteStride", item_size), "stride", item_size)
            if stride % size:
                raise ValueError("Unaligned accessor stride")
            vo = natural(v.get("byteOffset", 0), "view offset")
            vl = natural(v["byteLength"], "view length", 1)
            ao = natural(a.get("byteOffset", 0), "accessor offset")
            if vo+vl > self.bin_size or ao+(count-1)*stride+item_size > vl or (vo+ao) % size:
                raise ValueError("Accessor exceeds its view/buffer or is unaligned")
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError("Malformed or unsupported accessor") from e
        start = self.bin_start+vo+ao
        unpack = struct.Struct("<" + fmt*width)
        return a, count, lambda: (unpack.unpack_from(self.raw, start+i*stride) for i in range(count))

    def primitive(self, prim):
        if prim.get("mode", 4) != 4 or prim.get("extensions") or prim.get("targets"):
            raise ValueError("Only static, uncompressed TRIANGLES are supported")
        try:
            ai = prim["attributes"]["POSITION"]
        except (KeyError, TypeError) as e:
            raise ValueError("Missing POSITION") from e
        a, count, values = self.accessor(ai)
        if a["type"] != "VEC3" or a["componentType"] != 5126:
            raise ValueError("Expected FLOAT VEC3 POSITION")
        if ai not in self._bounds:
            lo, hi = [math.inf]*3, [-math.inf]*3
            for p in values():
                for i, v in enumerate(p):
                    if not math.isfinite(v):
                        raise ValueError("Nonfinite position")
                    lo[i], hi[i] = min(lo[i], v), max(hi[i], v)
            for key, actual in (("min", lo), ("max", hi)):
                declared = finite(a.get(key), 3, "POSITION bounds")
                if any(not math.isclose(v, w, rel_tol=1e-6, abs_tol=1e-7) for v, w in zip(declared, actual)):
                    raise ValueError("POSITION declared bounds disagree with bytes")
            self._bounds[ai] = {"min": lo, "max": hi}
        if "indices" in prim:
            ii = prim["indices"]
            key = (ii, count)
            a, ic, indices = self.accessor(ii)
            if a["type"] != "SCALAR" or a["componentType"] not in (5121, 5123, 5125) or ic % 3:
                raise ValueError("Invalid triangle indices")
            if key not in self._counts:
                if any(v[0] >= count for v in indices()):
                    raise ValueError("Triangle index exceeds POSITION count")
                self._counts[key] = ic
        else:
            ic = count
            if ic % 3:
                raise ValueError("Non-indexed triangle count is not divisible by three")
        return {"position_count": count, "triangles": ic//3, "bounds": self._bounds[ai]}

    def inspect(self):
        meshes = []
        for i, mesh in enumerate(self.doc.get("meshes", [])):
            prims = [self.primitive(p) for p in mesh["primitives"]]
            if not prims:
                raise ValueError("Empty mesh")
            meshes.append({"index": i, "name": mesh.get("name"), "primitives": prims,
                           "triangles": sum(p["triangles"] for p in prims),
                           "bounds": union([p["bounds"] for p in prims])})
        nodes = self.doc.get("nodes", [])
        parents = {}
        for i, node in enumerate(nodes):
            for child in node.get("children", []):
                natural(child, "child index")
                if child >= len(nodes) or child in parents:
                    raise ValueError("Invalid or multiple-parent node")
                parents[child] = i
        worlds = {}
        def world(i, active=None):
            if i in worlds:
                return worlds[i]
            active = set() if active is None else active
            if i in active:
                raise ValueError("Node cycle")
            active = active | {i}
            parent = world(parents[i], active) if i in parents else IDENTITY
            worlds[i] = product(parent, node_matrix(nodes[i]))
            return worlds[i]
        for i in range(len(nodes)):
            world(i)
        scenes = self.doc.get("scenes", [])
        scene = natural(self.doc.get("scene", 0), "scene")
        if scene >= len(scenes):
            raise ValueError("Missing default scene")
        selected = set()
        def select(i):
            natural(i, "scene node")
            if i >= len(nodes):
                raise ValueError("Invalid scene node")
            if i in selected:
                raise ValueError("Repeated scene node")
            selected.add(i)
            for child in nodes[i].get("children", []):
                select(child)
        for i in scenes[scene].get("nodes", []):
            if i in parents:
                raise ValueError("Scene root has a parent")
            select(i)
        observations = []
        for i, node in enumerate(nodes):
            mesh = node.get("mesh")
            if mesh is not None:
                natural(mesh, "mesh index")
                if mesh >= len(meshes):
                    raise ValueError("Invalid node mesh")
            observations.append({"index": i, "name": node.get("name"), "parent": parents.get(i),
                                 "mesh": mesh, "in_default_scene": i in selected,
                                 "world_matrix": worlds[i],
                                 "bounds": transformed_box(meshes[mesh]["bounds"], worlds[i]) if mesh is not None else None,
                                 "triangles": meshes[mesh]["triangles"] if mesh is not None else 0})
        boxes = [n["bounds"] for n in observations if n["in_default_scene"] and n["bounds"]]
        return {"format": "GLB 2.0", "coordinate_contract": "glTF right-handed Y-up; linear units meters",
                "anatomical_axis_registration": None, "bounds_method": "union of transformed local AABBs",
                "default_scene": scene, "bounds_m": union(boxes),
                "unique_mesh_count": len(meshes), "node_count": len(nodes),
                "mesh_instance_count": sum(n["mesh"] is not None and n["in_default_scene"] for n in observations),
                "unique_mesh_triangles": sum(m["triangles"] for m in meshes),
                "scene_triangles": sum(n["triangles"] for n in observations if n["in_default_scene"]),
                "asset": self.doc["asset"], "meshes": meshes, "nodes": observations,
                "anatomically_qualified": False, "fabrication_released": False}


@contextmanager
def open_glb(path):
    path = Path(path)
    size = path.stat().st_size
    if size < 20 or size > MAX_BYTES:
        raise ValueError("GLB outside size budget; materialize LFS first")
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        yield GLB(raw)


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()
