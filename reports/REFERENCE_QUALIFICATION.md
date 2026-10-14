# NIH female geometry — qualified scope

14 October 2026. Recovered from Git tree
`0e5de1cc04f17ee6d0d7e300f68bb391f13604ce`, committed as
`c9d1fe7112c11bf55fee60ec5ec7298e3ee5ed35` and retained by
[PR 1](https://github.com/SYSTEMS-OPERATOR/PHY-REF/pull/1).
The acquisition, original files, cached audits and previews were preserved.

## Original byte custody

| NIH entry | Entry / HRA version | File | Bytes | SHA-256 |
| --- | --- | --- | ---: | --- |
| [020984](https://3d.nih.gov/entries/3DPX-020984) | 2 / 1.2 | VH_F_Pelvis.glb | 1,593,336 | `155603d0c44a8ed1e0ca307f1ec3037941304f29f4187631135a9a150fab048d` |
| [020986](https://3d.nih.gov/entries/3DPX-020986) | 3 / 1.3 | 3d-vh-f-skin.glb | 16,003,176 | `b7dc8b3e5bae070f22f2619b10194b012a6f3cf930836d251828d5893e69594c` |
| [020992](https://3d.nih.gov/entries/3DPX-020992) | 2 / 1.5 | 3d-vh-f-united.glb | 211,624,968 | `472567a56896b9b7890508da6501fbf858e56aaa30745365f7a71ade782b529c` |

`sources/reference_assets.json` records publication, DOI, submission/file IDs,
original names, bounded public download routes and upstream storage URLs.
Pinned content hashes detect changes even when a public URL is mutable.
Entry versions and HRA object versions are recorded separately.

All three local originals and independent acquisition copies match. The body
LFS object also survived intact; a truncated working copy was preserved outside
the repository and restored from the matching original. Fresh acquisition reused
all verified files without downloading. A repeated audit matches every cached
report byte for byte.

The first recovery CI run passed contract tests, independently acquired all three
originals and reproduced the cached audits. Its upload step failed because
`git lfs push origin HEAD` could not obtain local refs in a detached checkout.
Commit `3576c8a8ae5766ab684a221813de13e0578003be` uploads only the exact catalog
object IDs. [The corrected run](https://github.com/SYSTEMS-OPERATOR/PHY-REF/actions/runs/38502010196)
passed. A fresh anonymous clone of that revision followed by `git lfs pull`
independently reproduced all three sizes and hashes. Remote LFS availability is
verified; no Git branch or main was pushed by the workflow.

## Structure, frames and limits

| Asset | Actual meshes / triangles | Supported anatomical scope | Qualification limit |
| --- | --- | --- | --- |
| Pelvis | 14 / 87,448 | Sacrum, coccyx and bilateral cortical/spongy pubis, ilium and ischium components | Tissue meshes represent four fused adult identities, not 14 bones; joint datums unreviewed |
| Skin | 1 / 266,696 | Exterior comparison surface | Cannot supply bone measurements or tissue mechanics |
| Body assembly | 888 / 5,557,599 | 91 skeletal-region meshes, including bone, cartilage and ligaments; pelvic/lower-limb structures and vertebrae | Not a complete 206-bone skeleton; lacks complete skull, ribs, upper limbs, hands and feet |

Full-body labels support 36 candidate canonical correspondences: C1–C7,
T1–T12, L1–L5, sacrum, coccyx, two fused hips and bilateral femur, tibia,
fibula and patella. This is source-label correspondence, not anatomy adoption.
The extra lumbar-6 label remains explicitly unmapped. It prevents assuming that
source L5 directly meets the sacrum in the canonical five-lumbar arrangement.

The [glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)
defines right-handed Y-up coordinates and linear meters. The cached inspector
records native node transforms and actual position/index bytes. Scene bounds
are unions of transformed local axis-aligned boxes; they are not osteometry or
necessarily tight world-space surface bounds after rotation. No anatomical
registration, accepted landmark coordinates or PHY transform is claimed.

Skin's native Y extent is 1657.7781439 mm. The
[HRA library description](https://humanatlas.io/3d-reference-library) gives the
Visible Human female donor stature as 1712 mm and describes medical illustration
and organ-expert review. That documentary lineage does not calibrate this
particular surface's posed Y extent or quantify segmentation error. The
relationship remains unresolved; neither number rescales SOPHY 1676.4 mm.
The models are not an age-28 average or experimentally qualified skeletal fit.

Actual aggregate counts differ from some NIH output-file counts. The archived
input files are not silently replaced with generated output meshes. Byte-level
parsing validates the declared static contract: GLB layout, supported accessors,
finite local bounds, index ranges, hierarchy and transforms. Manifold quality,
intersections, soft-tissue properties, anatomical accuracy and print suitability
remain separate unknowns.

## Rights and derivative fidelity

NIH entry metadata and the rendered license link identify CC BY 4.0. Attribution
to Kristen Browne and Heidi Schlehlein, HRA/HuBMAP and Visible Human/NLM lineage
is retained in `assets/nih/ATTRIBUTION.md`; the full license is adjacent. Sharing
and adaptation require attribution, license linkage and change identification.
Repository Unlicense does not replace asset terms. No source endorsement is
implied.

The six native projections in preview_views.png were visually inspected as
comparison views; no geometric qualification follows.

Two reduced native-frame previews survive unchanged: pelvis 19,983 triangles
and skin 25,000. Their manifest pins sources, recipe, dependency versions,
outputs, bounds and bidirectional sampled surface distances. Pelvis maximum
sampled error is about 0.95 mm; skin about 0.49 mm. These are sampled observations,
not global error bounds or approved landmark tolerances. Source labels and
material base colors are retained. Normals, vertex colors and textures are not
fully reproduced. Use originals for any future approved feature measurement.

## Admission decision and next evidence

**Admit for reproducible archival custody, static structural inspection and
native-frame visual comparison. Hold for canonical osteometry, joint placement,
contact geometry, mass/inertia and fabrication.** No numerical bone dimensions
are extracted from these meshes in this recovery.

The next bounded review should annotate a sacrum and one fused hemipelvis from
the original pelvis, with explicit anatomical definitions, vertex/face lineage,
native coordinates, measurement uncertainty and expert scale/segmentation review.
Only then can a registered datum packet be considered. The reference assets,
derived geometry, canonical constraints and later simulation models retain
separate authority. No physics-reference repository or deformable-body runtime
is needed to complete this evidence slice.
