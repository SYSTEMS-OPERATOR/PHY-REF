from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from phy_ref.glb import file_hash, open_glb, point
from phy_ref.landmarks import PACKET_PATH, load_packet, validate_draft


def draft_fixture():
    packet = load_packet(ROOT)
    with open_glb(ROOT / packet["preview"]["path"]) as glb:
        node = next(n for n in glb.inspect()["nodes"] if n["name"] == "VH_F_ilium_compact_bone_L")
        prim = glb.doc["meshes"][node["mesh"]]["primitives"][0]
        _, _, indices = glb.accessor(prim["indices"])
        vertices = [v[0] for v in indices()][:3]
        _, _, positions = glb.accessor(prim["attributes"]["POSITION"])
        points = list(positions())
        xyz = point(node["world_matrix"], [sum(points[j][i] for j in vertices) / 3 for i in range(3)])
        annotation = {"landmark_id": "L_ASIS", "mesh_name": node["name"],
                      "preview_node": node["index"], "source_node": 13,
                      "face_index": 0, "vertex_indices": vertices,
                      "barycentric": [1/3]*3, "native_point_m": xyz,
                      "original_face_index": None, "anatomically_accepted": False}
    return {"kind": "PHY_PELVIS_PREVIEW_DRAFT_V1", "packet_id": packet["packet_id"],
            "packet_sha256": file_hash(ROOT / PACKET_PATH),
            "source_sha256": packet["source"]["sha256"], "preview_sha256": packet["preview"]["sha256"],
            "reference_revision": packet["reference_baseline_revision"], "annotations": [annotation],
            "accepted_landmarks": None, "canonical_transform": None, "fabrication_released": False}


class LandmarkReviewTest(unittest.TestCase):
    def test_packet_keeps_five_definitions_and_unknown_acceptance(self):
        packet = load_packet(ROOT)
        self.assertEqual(len(packet["landmarks"]), 5)
        self.assertIsNone(packet["accepted_landmarks"])
        self.assertEqual(len(packet["crosswalk"]["BONE_HIP_L"]), 6)
        self.assertTrue(all(v is None for v in packet["required_evidence"].values()))

    def test_reconstructs_preview_point_without_anatomical_acceptance(self):
        result = validate_draft(ROOT, draft_fixture())
        self.assertEqual(result["annotations"], 1)
        self.assertFalse(result["anatomically_accepted"])

    def test_empty_draft_remains_unaccepted(self):
        draft = draft_fixture(); draft["annotations"] = []
        self.assertEqual(validate_draft(ROOT, draft)["annotations"], 0)

    def test_custody_and_promotion_rejected(self):
        for key, value in [("packet_sha256", "0"*64), ("source_sha256", "0"*64),
                           ("preview_sha256", "0"*64), ("reference_revision", "main"),
                           ("canonical_transform", []), ("fabrication_released", True),
                           ("accepted_landmarks", [])]:
            draft = draft_fixture(); draft[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_draft(ROOT, draft)

    def test_wrong_face_label_node_and_point_rejected(self):
        mutations = {"landmark_id": "L_UNKNOWN", "mesh_name": "VH_F_ilium_compact_bone_R",
                     "preview_node": 0, "source_node": 12, "face_index": -1,
                     "vertex_indices": [0, 0, 0], "barycentric": [-1, 1, 1],
                     "native_point_m": [float("nan"), 0, 0],
                     "original_face_index": 0, "anatomically_accepted": True}
        for key, value in mutations.items():
            draft = draft_fixture(); draft["annotations"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_draft(ROOT, draft)
        draft = draft_fixture(); draft["annotations"][0]["native_point_m"][0] += .001
        with self.assertRaisesRegex(ValueError, "reconstruct"):
            validate_draft(ROOT, draft)

    def test_duplicate_landmarks_rejected(self):
        draft = draft_fixture(); draft["annotations"] *= 2
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_draft(ROOT, draft)


if __name__ == "__main__":
    unittest.main()
