"""Independent original-buffer review reconstruction. No anatomical acceptance."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

from .glb import GLB, point, strict_json
from .landmarks import load_packet, PACKET_PATH

CONTRACT_PATH = 'reviews/original_review_contract.json'
GATES = ['independent_anatomical_review', 'metric_calibration', 'segmentation_review',
         'approved_uncertainty_budget', 'anatomical_acceptance', 'canonical_registration', 'source_L6_context']


def keys(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError('Unsupported fields: ' + label)


def text(value, label, limit=8192):
    if not isinstance(value, str) or len(value) > limit or '\x00' in value:
        raise ValueError('Invalid text: ' + label)


def vector(value, label):
    if (not isinstance(value, list) or len(value) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in value)):
        raise ValueError('Invalid finite vector: ' + label)


def index(value, size, label):
    if type(value) is not int or not 0 <= value < size:
        raise ValueError('Invalid index: ' + label)
    return value


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode()


class Surface:
    """Read original accessor indices and full parent transforms, without repair."""
    def __init__(self, raw):
        self.glb = GLB(raw)
        self.inspection = self.glb.inspect()
        self.nodes = {n['index']: n for n in self.inspection['nodes'] if n['in_default_scene'] and n['mesh'] is not None}
        self.cache = {}

    def triangle(self, node_id, primitive_id, face_id, vertices=None):
        index(node_id, len(self.glb.doc['nodes']), 'source node')
        if node_id not in self.nodes:
            raise ValueError('Source node outside default scene')
        node = self.nodes[node_id]
        prims = self.glb.doc['meshes'][node['mesh']]['primitives']
        index(primitive_id, len(prims), 'primitive')
        key = (node_id, primitive_id)
        if key not in self.cache:
            prim = prims[primitive_id]
            if 'indices' not in prim:
                raise ValueError('Original review requires indexed triangles')
            _, _, positions = self.glb.accessor(prim['attributes']['POSITION'])
            _, _, indices = self.glb.accessor(prim['indices'])
            self.cache[key] = (list(positions()), [v[0] for v in indices()])
        positions, indices = self.cache[key]
        index(face_id, len(indices)//3, 'face')
        actual = indices[face_id*3:face_id*3+3]
        if vertices is not None and (not isinstance(vertices, list) or len(vertices) != 3
                or any(type(v) is not int for v in vertices) or vertices != actual):
            raise ValueError('Original triangle vertex lineage mismatch')
        triangle = [point(node['world_matrix'], positions[i]) for i in actual]
        u = [triangle[1][i]-triangle[0][i] for i in range(3)]
        v = [triangle[2][i]-triangle[0][i] for i in range(3)]
        cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        if sum(x*x for x in cross) == 0:
            raise ValueError('Degenerate original triangle')
        return actual, triangle


class OriginalReview:
    def __init__(self, root, original, revision=None):
        self.root = Path(root)
        self.packet = load_packet(root)
        raw_contract = (self.root/CONTRACT_PATH).read_bytes()
        self.contract = strict_json(raw_contract)
        self.contract_sha = hashlib.sha256(raw_contract).hexdigest()
        c = self.contract
        if (c['version'] != 'PHY_PELVIS_ORIGINAL_CONTRACT_V1'
                or c['packet_sha256'] != hashlib.sha256((self.root/PACKET_PATH).read_bytes()).hexdigest()
                or c['source'] != {k:self.packet['source'][k] for k in ('asset_id','bytes','sha256')}
                or set(c['features']) != {f['id'] for f in self.packet['landmarks']}
                or c['units'] != 'm' or c['coordinate_frame'] != self.packet['coordinate_frame']
                or c['accepted_landmarks'] is not None or c['canonical_transform'] is not None
                or c['fabrication_released'] is not False):
            raise ValueError('Original contract custody or qualification mismatch')
        if revision is None:
            revision = subprocess.check_output(['git','-C',str(self.root),'rev-parse','HEAD'],text=True).strip()
        if not isinstance(revision,str) or not re.fullmatch('[0-9a-f]{40}',revision):
            raise ValueError('Expected immutable reference revision')
        self.revision = revision
        p = Path(original)
        if p.stat().st_size != c['source']['bytes']:
            raise ValueError('Original missing, LFS pointer or size mismatch')
        raw = p.read_bytes()
        if hashlib.sha256(raw).hexdigest() != c['source']['sha256']:
            raise ValueError('Original checksum mismatch')
        self.surface = Surface(raw)
        for ident, f in c['features'].items():
            n = self.surface.nodes.get(f['source_node'])
            definition = next(d for d in self.packet['landmarks'] if d['id'] == ident)
            if not n or n['name'] != f['mesh_name'] or f['mesh_name'] not in definition['preview_mesh_names']:
                raise ValueError('Original feature node/label mismatch')

    def header(self, kind):
        return {'kind':kind,'contract_sha256':self.contract_sha,'packet_id':self.packet['packet_id'],
                'packet_sha256':self.contract['packet_sha256'],'reference_revision':self.revision,
                'source_sha256':self.contract['source']['sha256'],'units':'m',
                'coordinate_frame':self.contract['coordinate_frame'],'accepted_landmarks':None,
                'canonical_transform':None,'fabrication_released':False}

    def empty(self, reviewer='unassigned', session='session-1', evidence_kind='review_submission'):
        return {**self.header(self.contract['draft_kind']), 'reviewer':{'id':reviewer,'session_id':session,'evidence_kind':evidence_kind},
                'annotations':[],'views':[],'review_notes':''}

    def validate(self, draft):
        base = self.header(self.contract['draft_kind'])
        keys(draft, ' '.join(base)+' reviewer annotations views review_notes', 'original draft')
        if any(type(draft[k]) is not type(v) or draft[k] != v for k,v in base.items()):
            raise ValueError('Original draft custody, frame or qualification mismatch')
        if len(json_bytes(draft)) > self.contract['max_draft_bytes']:
            raise ValueError('Original draft exceeds byte budget')
        keys(draft['reviewer'], 'id session_id evidence_kind', 'reviewer')
        for k in ('id','session_id'):
            v = draft['reviewer'][k]
            if not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}',v):
                raise ValueError('Invalid reviewer/session identifier')
        if draft['reviewer']['evidence_kind'] not in ('review_submission','software_fixture'):
            raise ValueError('Invalid declared evidence kind')
        text(draft['review_notes'],'review notes')
        views = draft['views']
        if not isinstance(views,list) or len(views) > self.contract['max_views']:
            raise ValueError('Invalid view list')
        for view in views:
            keys(view,'label camera_position_mm target_mm','view')
            text(view['label'],'view label',80)
            vector(view['camera_position_mm'],'camera'); vector(view['target_mm'],'target')
        annotations = draft['annotations']
        if not isinstance(annotations,list) or len(annotations) > len(self.contract['features']):
            raise ValueError('Invalid original annotation list')
        seen, pending = set(), []
        for a in annotations:
            keys(a,'landmark_id mesh_name source_node primitive_index face_index vertex_indices barycentric native_point_m selection_rule patch_faces patch_rule construction_note anatomically_accepted','annotation')
            ident = a['landmark_id']
            if not isinstance(ident,str) or ident not in self.contract['features'] or ident in seen:
                raise ValueError('Unknown or duplicate original landmark')
            seen.add(ident); f = self.contract['features'][ident]
            if (a['mesh_name'] != f['mesh_name'] or type(a['source_node']) is not int
                    or a['source_node'] != f['source_node'] or a['anatomically_accepted'] is not False):
                raise ValueError('Wrong original surface or anatomical promotion')
            _, triangle = self.surface.triangle(a['source_node'],a['primitive_index'],a['face_index'],a['vertex_indices'])
            w, xyz = a['barycentric'], a['native_point_m']
            vector(w,'barycentric'); vector(xyz,'native point')
            eps = self.contract['reconstruction_epsilon_m']
            if min(w) < -1e-7 or max(w) > 1+1e-7 or abs(sum(w)-1) > 1e-7:
                raise ValueError('Barycentric point outside original triangle')
            reconstructed = [sum(w[j]*triangle[j][i] for j in range(3)) for i in range(3)]
            if math.dist(reconstructed,xyz) > eps:
                raise ValueError('Original point does not reconstruct')
            for k in ('selection_rule','patch_rule','construction_note'):
                text(a[k],k,2000)
            patches = a['patch_faces']
            if not isinstance(patches,list) or len(patches) > self.contract['max_patch_faces']:
                raise ValueError('Invalid patch face budget')
            faces = set()
            for face in patches:
                keys(face,'primitive_index face_index vertex_indices','patch face')
                self.surface.triangle(a['source_node'],face['primitive_index'],face['face_index'],face['vertex_indices'])
                key = (face['primitive_index'],face['face_index'])
                if key in faces: raise ValueError('Duplicate patch face')
                faces.add(key)
            if not a['selection_rule'].strip(): pending.append(ident+': point-selection rule')
            if f['patch_required'] and (not patches or not a['patch_rule'].strip()): pending.append(ident+': patch and representative-point rule')
            if f['construction_required'] and not a['construction_note'].strip(): pending.append(ident+': median-plane construction')
        return {'status':'original_geometry_verified_only','annotations':len(annotations),
                'missing_features':sorted(set(self.contract['features'])-seen),'unresolved_requirements':sorted(pending),
                'anatomically_accepted':False,'fabrication_released':False}

    def compare(self, a, b):
        self.validate(a); self.validate(b)
        aa = {p['landmark_id']:p for p in a['annotations']}; bb = {p['landmark_id']:p for p in b['annotations']}
        rows = []
        for ident in sorted(self.contract['features']):
            x,y = aa.get(ident),bb.get(ident)
            row = {'landmark_id':ident,'status':'paired' if x and y else 'missing_both' if not x and not y else 'missing_a' if not x else 'missing_b',
                   'distance_source_mm':None,'selection_rules_differ':None,'patch_faces_differ':None}
            if x and y:
                row.update(distance_source_mm=math.dist(x['native_point_m'],y['native_point_m'])*1000,
                           selection_rules_differ=any(x[k]!=y[k] for k in ('selection_rule','patch_rule','construction_note')),
                           patch_faces_differ=sorted((f['primitive_index'],f['face_index']) for f in x['patch_faces']) != sorted((f['primitive_index'],f['face_index']) for f in y['patch_faces']))
            rows.append(row)
        return {'kind':self.contract['comparison_kind'],'status':'unaccepted_coordinate_comparison',
                'reviewer_relation':'same_declared_reviewer' if a['reviewer']['id']==b['reviewer']['id'] else 'distinct_declared_ids_independence_unverified',
                'contains_software_fixtures':any(d['reviewer']['evidence_kind']=='software_fixture' for d in (a,b)),
                'distance_meaning':'Source-coordinate distances converted to mm; metric calibration unresolved; no tolerance verdict.',
                'rows':rows,'accepted_landmarks':None,'canonical_transform':None,'fabrication_released':False}

    def make_packet(self, reviews, viewer_build_sha256=None):
        if not isinstance(reviews,list) or not 1 <= len(reviews) <= 2: raise ValueError('One or two reviews required')
        if viewer_build_sha256 is not None and (not isinstance(viewer_build_sha256,str) or not re.fullmatch('[0-9a-f]{64}',viewer_build_sha256)):
            raise ValueError('Invalid viewer build fingerprint')
        return {**self.header(self.contract['packet_kind']),'reviews':deepcopy(reviews),
                'validation':[self.validate(d) for d in reviews],
                'comparison':self.compare(*reviews) if len(reviews)==2 else None,
                'viewer_build_sha256':viewer_build_sha256,'unresolved_gates':GATES,
                'attribution':self.packet['source']['attribution'],'license':'CC-BY-4.0'}

    def validate_packet(self, packet):
        if not isinstance(packet,dict): raise ValueError('Packet must be an object')
        expected = self.make_packet(packet.get('reviews'),packet.get('viewer_build_sha256'))
        def equal(a,b):
            if isinstance(a,dict) and isinstance(b,dict): return set(a)==set(b) and all(equal(a[k],b[k]) for k in a)
            if isinstance(a,list) and isinstance(b,list): return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
            if type(a) in (int,float) and type(b) in (int,float): return math.isfinite(a) and math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-9)
            return type(a) is type(b) and a==b
        if len(json_bytes(packet)) > self.contract['max_packet_bytes'] or not equal(packet,expected):
            raise ValueError('Packet reports/custody/qualification differ from reconstruction')
        return {'status':'original_review_packet_verified_only','reviews':len(packet['reviews']),
                'anatomically_accepted':False,'fabrication_released':False}
