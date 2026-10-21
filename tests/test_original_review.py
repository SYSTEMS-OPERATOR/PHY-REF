"""Software fixtures only. No selected point is an anatomical observation."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

from phy_ref.glb import strict_json
from phy_ref.original_review import OriginalReview, Surface, json_bytes

ROOT = Path(__file__).resolve().parents[1]


def transformed_fixture():
    raw = struct.pack('<9f3H',0,0,0,1,0,0,0,1,0,0,1,2)
    raw += b'\0' * (-len(raw)%4)
    doc = {'asset':{'version':'2.0'},'buffers':[{'byteLength':len(raw)}],
           'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':36},{'buffer':0,'byteOffset':36,'byteLength':6}],
           'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[0,0,0],'max':[1,1,0]},
                        {'bufferView':1,'componentType':5123,'count':3,'type':'SCALAR'}],
           'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1}]}],
           'nodes':[{'translation':[2,3,4],'scale':[2,2,2],'children':[1]},
                    {'name':'fixture','mesh':0,'translation':[1,0,0]}],
           'scenes':[{'nodes':[0]}],'scene':0}
    text = json.dumps(doc,separators=(',',':')).encode(); text += b' '*(-len(text)%4)
    return struct.pack('<4sII',b'glTF',2,28+len(text)+len(raw))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(raw),0x004e4942)+raw


class OriginalGeometryTest(unittest.TestCase):
    def test_parent_transform_and_exact_triangle_indices(self):
        surface = Surface(transformed_fixture())
        indices, triangle = surface.triangle(1,0,0,[0,1,2])
        self.assertEqual(indices,[0,1,2])
        self.assertEqual(triangle,[[4,3,4],[6,3,4],[4,5,4]])
        for args in ((True,0,0,None),(1,False,0,None),(1,0,True,None),(1,0,-1,None),(1,0,0,[0,2,1]),(0,0,0,None)):
            with self.subTest(args=args),self.assertRaises(ValueError): surface.triangle(*args)

    def test_strict_json_rejects_duplicates_and_nonfinite(self):
        for value in ('{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}'):
            with self.subTest(value=value),self.assertRaises(ValueError): strict_json(value)


class PinnedOriginalReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = os.environ.get('PHY_PELVIS_ORIGINAL')
        if not value: raise unittest.SkipTest('Explicit PHY_PELVIS_ORIGINAL required for original-buffer integration checks')
        cls.path = Path(value)
        cls.ctx = OriginalReview(ROOT,cls.path)

    def draft(self,ident='L_ASIS',weights=None,reviewer='fixture-A'):
        c = self.ctx; d = c.empty(reviewer,'fixture-session','software_fixture')
        f = c.contract['features'][ident]
        for face in range(100):
            try: vertices,triangle = c.surface.triangle(f['source_node'],0,face); break
            except ValueError: pass
        w = weights or [.2,.3,.5]
        d['annotations'] = [{'landmark_id':ident,'mesh_name':f['mesh_name'],'source_node':f['source_node'],
                             'primitive_index':0,'face_index':face,'vertex_indices':vertices,'barycentric':w,
                             'native_point_m':[sum(w[j]*triangle[j][i] for j in range(3)) for i in range(3)],
                             'selection_rule':'Software fixture: arbitrary cortical triangle, not an anatomical landmark.',
                             'patch_faces':[{'primitive_index':0,'face_index':face,'vertex_indices':vertices}],
                             'patch_rule':'Software fixture: explicitly selected original triangle.',
                             'construction_note':'','anatomically_accepted':False}]
        d['views'] = [{'label':'fixture','camera_position_mm':[300,200,400],'target_mm':[0,0,0]}]
        return d

    def test_five_surfaces_reconstruct_and_stay_unaccepted(self):
        for ident in self.ctx.contract['features']:
            with self.subTest(ident=ident):
                result = self.ctx.validate(self.draft(ident))
                self.assertEqual(result['status'],'original_geometry_verified_only')
                self.assertFalse(result['anatomically_accepted'])
        self.assertIn('SACRAL_PROMONTORY: median-plane construction',self.ctx.validate(self.draft('SACRAL_PROMONTORY'))['unresolved_requirements'])

    def test_draft_round_trip_and_partial_work(self):
        d = self.draft('L_ISCHIAL_TUBEROSITY')
        self.assertEqual(strict_json(json_bytes(d)),d)
        d['annotations'][0]['patch_faces'] = []
        self.assertIn('L_ISCHIAL_TUBEROSITY: patch and representative-point rule',self.ctx.validate(d)['unresolved_requirements'])
        self.assertEqual(self.ctx.validate(self.ctx.empty())['annotations'],0)

    def test_source_and_frame_custody_fail_closed(self):
        for key,value in [('kind','PHY_PELVIS_PREVIEW_DRAFT_V1'),('source_sha256','0'*64),('contract_sha256','0'*64),
                          ('packet_sha256','0'*64),('reference_revision','0'*40),('units','mm'),('coordinate_frame','centered'),
                          ('accepted_landmarks',[]),('canonical_transform',[]),('fabrication_released',True),('extra',False)]:
            d = self.draft(); d[key] = value
            with self.subTest(key=key),self.assertRaises(ValueError): self.ctx.validate(d)

    def test_bad_triangle_patch_and_claims_rejected(self):
        for key,value in [('source_node',12),('primitive_index',True),('face_index',-1),('vertex_indices',[0,0,0]),
                          ('barycentric',[-.1,.2,.9]),('native_point_m',[0,float('inf'),0]),('mesh_name','wrong'),
                          ('anatomically_accepted',True),('preview_node',1),('selection_rule',42)]:
            d = self.draft(); d['annotations'][0][key] = value
            with self.subTest(key=key),self.assertRaises(ValueError): self.ctx.validate(d)
        for mutate in ('duplicate_annotation','duplicate_patch','moved_point','bad_patch','huge_patch','reviewer','views'):
            d = self.draft(); a = d['annotations'][0]
            if mutate=='duplicate_annotation': d['annotations'] *= 2
            if mutate=='duplicate_patch': a['patch_faces'] *= 2
            if mutate=='moved_point': a['native_point_m'][0] += .001
            if mutate=='bad_patch': a['patch_faces'][0]['face_index'] = -1
            if mutate=='huge_patch': a['patch_faces'] *= 257
            if mutate=='reviewer': d['reviewer']['evidence_kind'] = 'anatomically_accepted'
            if mutate=='views': d['views'][0]['target_mm'] = [0,0,float('nan')]
            with self.subTest(mutate=mutate),self.assertRaises(ValueError): self.ctx.validate(d)

    def test_source_bytes_and_lfs_pointer_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'original.glb'
            for raw in (b'version https://git-lfs.github.com/spec/v1\n',self.path.read_bytes()[:-1],self.path.read_bytes()[:-1]+b'X'):
                p.write_bytes(raw)
                with self.assertRaises(ValueError): OriginalReview(ROOT,p)

    def test_comparison_is_non_destructive_and_never_accepts(self):
        a = self.draft(); b = self.draft(weights=[.1,.3,.6],reviewer='fixture-B')
        before = deepcopy([a,b]); result = self.ctx.compare(a,b)
        self.assertEqual([a,b],before)
        paired = next(r for r in result['rows'] if r['landmark_id']=='L_ASIS')
        self.assertGreater(paired['distance_source_mm'],0)
        self.assertTrue(result['contains_software_fixtures'])
        self.assertEqual(self.ctx.compare(a,a)['reviewer_relation'],'same_declared_reviewer')
        b['annotations'] = []
        self.assertEqual(next(r for r in self.ctx.compare(a,b)['rows'] if r['landmark_id']=='L_ASIS')['status'],'missing_b')
        b['source_sha256'] = '0'*64
        with self.assertRaises(ValueError): self.ctx.compare(a,b)

    def test_deterministic_packet_and_forged_reports(self):
        reviews = [self.draft(),self.draft(reviewer='fixture-B')]
        packet = self.ctx.make_packet(reviews,'a'*64)
        self.assertEqual(json_bytes(packet),json_bytes(self.ctx.make_packet(reviews,'a'*64)))
        self.assertEqual(self.ctx.validate_packet(packet)['reviews'],2)
        for mutate in ('distance','gates','accepted','report','build','extra'):
            bad = deepcopy(packet)
            if mutate=='distance': next(r for r in bad['comparison']['rows'] if r['landmark_id']=='L_ASIS')['distance_source_mm'] = 99
            if mutate=='gates': bad['unresolved_gates'] = []
            if mutate=='accepted': bad['accepted_landmarks'] = []
            if mutate=='report': bad['validation'][0]['status'] = 'anatomically_accepted'
            if mutate=='build': bad['viewer_build_sha256'] = 'not-a-hash'
            if mutate=='extra': bad['approved_tolerance_mm'] = 1
            with self.subTest(mutate=mutate),self.assertRaises(ValueError): self.ctx.validate_packet(bad)


if __name__ == '__main__': unittest.main()
