import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from phy_ref.glb import GLB, IDENTITY, node_matrix, strict_json
from phy_ref.catalog import load, local_path, validate, verify_file
from tools.acquire_nih import acquire


def fixture():
    positions = [(-1., 0., 0.), (1., 0., 0.), (0., 1., 0.)]
    binary = b"".join(struct.pack("<3f", *p) for p in positions) + struct.pack("<3I", 0, 1, 2)
    doc = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(binary)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36},
                           {"buffer": 0, "byteOffset": 36, "byteLength": 12}],
           "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3,
                          "type": "VEC3", "min": [-1, 0, 0], "max": [1, 1, 0]},
                         {"bufferView": 1, "componentType": 5125, "count": 3, "type": "SCALAR"}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
           "nodes": [{"name": "root", "translation": [0, 2, 0], "children": [1]},
                     {"name": "triangle", "mesh": 0, "scale": [2, 2, 2]}],
           "scenes": [{"nodes": [0]}], "scene": 0}
    return doc, binary


def pack(doc, binary):
    raw = json.dumps(doc).encode()
    raw += b" " * (-len(raw) % 4)
    binary += b"\0" * (-len(binary) % 4)
    length = 12+8+len(raw)+8+len(binary)
    return (struct.pack("<4sII", b"glTF", 2, length)
            + struct.pack("<II", len(raw), 0x4E4F534A) + raw
            + struct.pack("<II", len(binary), 0x004E4942) + binary)


class GeometryTests(unittest.TestCase):
    def test_actual_bounds_counts_and_parent_transform(self):
        doc, binary = fixture()
        result = GLB(pack(doc, binary)).inspect()
        self.assertEqual(result["scene_triangles"], 1)
        self.assertEqual(result["bounds_m"], {"min": [-2, 2, 0], "max": [2, 4, 0]})
        self.assertIsNone(result["anatomical_axis_registration"])
        self.assertFalse(result["fabrication_released"])

    def test_bad_header_and_truncation(self):
        doc, binary = fixture()
        raw = pack(doc, binary)
        for bad in [raw[:-1], b"bad!" + raw[4:], b"version https://git-lfs.github.com/spec/v1\n"]:
            with self.subTest(raw=bad[:12]), self.assertRaises(ValueError):
                GLB(bad)

    def test_geometry_mutations_fail(self):
        original, binary = fixture()
        mutations = [
            lambda d: d["accessors"][0].update(count=100),
            lambda d: d["accessors"][0].update(min=[-2, 0, 0]),
            lambda d: d["accessors"][0].update(componentType=5123),
            lambda d: d["accessors"][0].update(sparse={"count": 1}),
            lambda d: d["accessors"][1].update(count=2),
            lambda d: d["bufferViews"][0].update(byteStride=13),
            lambda d: d["meshes"][0]["primitives"][0].update(mode=1),
            lambda d: d.update(extensionsRequired=["KHR_draco_mesh_compression"]),
            lambda d: d["buffers"][0].update(uri="external.bin"),
            lambda d: d.update(skins=[{}]),
            lambda d: d["nodes"][1].update(mesh=99),
            lambda d: d["nodes"][1].update(children=[0]),
            lambda d: d["scenes"][0].update(nodes=[0, 1]),
            lambda d: d["nodes"][1].update(rotation=[1, 1, 1, 1]),
            lambda d: d["nodes"][1].update(matrix=list(range(16))),
        ]
        for mutation in mutations:
            doc = copy.deepcopy(original)
            mutation(doc)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                GLB(pack(doc, binary)).inspect()

    def test_out_of_range_indices_and_nonfinite_vertices(self):
        doc, binary = fixture()
        for bad in [binary[:36]+struct.pack("<3I", 0, 1, 3),
                    struct.pack("<f", float("inf"))+binary[4:]]:
            with self.assertRaises(ValueError):
                GLB(pack(doc, bad)).inspect()

    def test_matrix_trs_and_json_ambiguity(self):
        with self.assertRaises(ValueError):
            node_matrix({"matrix": [1, 0, 0, 0]*4, "translation": [0, 0, 0]})
        for raw in ['{"x":1,"x":2}', '{"x":NaN}']:
            with self.assertRaises(ValueError):
                strict_json(raw)
        self.assertEqual(node_matrix({}), IDENTITY)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load(ROOT/"sources/reference_assets.json")

    def test_real_catalog_keeps_three_unregistered_assets(self):
        assets = validate(self.catalog)
        self.assertEqual(len(assets), 3)
        self.assertEqual([a["entry_version"] for a in assets], [2, 3, 2])

    def test_catalog_mutations(self):
        changes = [
            ("license", "Unlicense"), ("license_evidence", None),
            ("canonical_transform", IDENTITY), ("anatomically_qualified", True),
            ("fabrication_released", True), ("disposition", "approved"),
            ("bytes", True), ("sha256", "f"*63),
            ("path", "../../outside.glb"), ("download_url", "https://example.com/model.glb"),
            ("entry_url", "https://3d.nih.gov/entries/3DPX-000000"),
            ("entry_version", "2"),
        ]
        for key, value in changes:
            data = copy.deepcopy(self.catalog);data["assets"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(data)
        data = copy.deepcopy(self.catalog);data["assets"].append(data["assets"][0])
        with self.assertRaises(ValueError):
            validate(data)

    def test_paths_reject_absolute_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for path in ["/tmp/file.glb", "../file.glb", "a\\b.glb"]:
                with self.assertRaises(ValueError):
                    local_path(root, path)
            (root/"link").symlink_to("/tmp")
            with self.assertRaises(ValueError):
                local_path(root, "link/file.glb")

    def test_integrity_checks_actual_bytes(self):
        doc, binary = fixture();raw = pack(doc, binary)
        asset = dict(self.catalog["assets"][0], path="test.glb", bytes=len(raw),
                     sha256=hashlib.sha256(raw).hexdigest())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"test.glb"
            path.write_bytes(raw)
            self.assertEqual(verify_file(temp, asset), path)
            path.write_bytes(raw[:-1])
            with self.assertRaises(ValueError):
                verify_file(temp, asset)
            path.write_bytes(raw[:-1]+b"x")
            with self.assertRaises(ValueError):
                verify_file(temp, asset)

    def test_download_hash_mismatch_preserves_lfs_pointer(self):
        doc, binary = fixture();raw = pack(doc, binary)
        asset = dict(self.catalog["assets"][0], path="test.glb", bytes=len(raw),
                     sha256=hashlib.sha256(raw).hexdigest())
        class Response(io.BytesIO):
            def geturl(self):
                return "https://3d.nih.gov/api/download"
        with tempfile.TemporaryDirectory() as temp:
            pointer = b"version https://git-lfs.github.com/spec/v1\n"
            path = Path(temp)/"test.glb";path.write_bytes(pointer)
            with self.assertRaises(ValueError):
                acquire(temp, asset, lambda *a, **k: Response(raw[:-1]+b"x"))
            self.assertEqual(path.read_bytes(), pointer)
            self.assertEqual(list(Path(temp).iterdir()), [path])
            self.assertEqual(acquire(temp, asset, lambda *a, **k: Response(raw)), "downloaded_and_verified")
            self.assertEqual(path.read_bytes(), raw)

    def test_download_budget_and_nonpointer_no_overwrite(self):
        doc, binary = fixture();raw = pack(doc, binary)
        asset = dict(self.catalog["assets"][0], path="test.glb", bytes=len(raw),
                     sha256=hashlib.sha256(raw).hexdigest())
        class Response(io.BytesIO):
            def geturl(self):
                return "https://3d.nih.gov/api/download"
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                acquire(temp, asset, lambda *a, **k: Response(raw+b"x"))
            self.assertFalse((Path(temp)/"test.glb").exists())
            path = Path(temp)/"test.glb";path.write_bytes(b"existing invalid content")
            with self.assertRaises(ValueError):
                acquire(temp, asset, lambda *a, **k: Response(raw))
            self.assertEqual(path.read_bytes(), b"existing invalid content")


if __name__ == "__main__":
    unittest.main()
