# Original pelvic review contract and development log

Directive: PHY-DEV-PELVIS-REVIEW-001, authorized by SYSOP. Base PHY-REF main:
`f2f9ffcb7bd0970506eb42b2e325eec1a89ffe71`; PHY main:
`b936b6c7db329408e4da0f4cfb91532201ce3433`. Existing source/preview files and
pending anatomical packet are preserved.

## New formats

`reviews/original_review_contract.json` introduces separate V1 original draft,
comparison and packet kinds. It binds the existing definition packet, exact
original bytes and five cortical surface labels. The loaded checkout's immutable
HEAD is the expected reference revision; use the pinned checkout when validating
Studio output. All qualification fields remain false/null. The preview V1 format
and independent preview checker retain their existing behavior.

An original point records node, primitive, original face and vertex indices,
barycentric weights and native world meters. A patch is an explicit list of
primitive/face/vertex references on that same cortical node. Point-selection,
patch/representative-point rules and construction notes are reviewer submissions.
Empty drafts and incomplete patch/construction work can be resumed; validation
reports unresolved requirements without inventing a representative point or plane.

Native FLOAT32 source geometry is reconstructed with original parent transforms.
The numerical position consistency limit is 1e-7 meters (0.0001 display mm),
chosen to admit FLOAT32/browser arithmetic around the source's sub-meter extent.
It is not metric calibration, anatomical error, a decimation bound or an accepted
manufacturing tolerance. Barycentric sum/bounds use 1e-7 numerical slack.
Cross-language calculated comparison reports allow 1e-9 mm absolute arithmetic
roundoff (1e-12 relative). Stored annotation coordinates are never rounded.

Budgets: exact 1,593,336-byte original; 512 KiB draft; 2 MiB packet; five
annotations per review; 256 explicit patch faces per feature; twelve recorded
camera views; two supplied reviews per packet. Only indexed static embedded
triangles are admitted. No mesh rewriting, remote buffers, automatic acquisition,
canonical fitting or image-derived feature inference is added.

Reviewer/session IDs are declared identifiers, not verified independence. Fixture
evidence is labeled `software_fixture`. Comparison preserves both inputs, reports
missing features and source-coordinate distances converted to mm, and gives no
tolerance verdict, average or accepted coordinate. Same-declared-reviewer pairs
are explicitly identified. Calibration and uncertainty proposals belong in review
notes until a later evidence/acceptance decision.

Packet JSON contains one/two reviews, independently reproducible validation and
comparison reports, source/definition/contract/build fingerprints, attribution
and unresolved gates. No absolute paths, implicit timestamps or original GLB bytes
are embedded. Camera records use display mm; annotations remain native meters.
Canonical sorted JSON is deterministic within a producer; validators compare
parsed content and independently reconstruct reports, not serialization spelling.

## Development order and checks

1. Pin source custody, contract and independent original-buffer reconstruction.
2. Exercise original triangles/patches and negative tamper tests before UI work.
3. Integrate explicit local loading, separate original mode, capture/patch editing,
   draft reload, declared reviewer comparison and packet export in PHY Studio.
4. Test actual browser clicks, offline use, 390 px controls, camera/resize behavior,
   geometry preservation and repeat builds; publish linked PRs, never auto-merge.

```bash
python -m unittest discover -s tests -v
PHY_PELVIS_ORIGINAL=/path/to/VH_F_Pelvis.glb python -m unittest discover -s tests -v
python tools/validate_original_review.py --original /path/to/VH_F_Pelvis.glb
python tools/validate_original_review.py --original /path/to/VH_F_Pelvis.glb --draft review-A.json --compare review-B.json --output packet.json
python tools/validate_original_review.py --original /path/to/VH_F_Pelvis.glb --packet packet.json
```

Original integration tests explicitly skip when no original is supplied. Normal
Actions acquires the already pinned originals and reruns the complete suite with
the pelvis path supplied. No synthetic point is an anatomical observation.
