# PHY-REF

External reference geometry and provenance for SYSTEMS-OPERATOR/PHY. Production
canon, embodiment dimensions, mechanics and fabrication decisions stay in PHY.

Three original NIH/Human Reference Atlas female GLBs are archived in
assets/nih/originals with original filenames and independent SHA-256 checks.
The public NIH download route provides input meshes; regenerated NIH output
files are not substituted. Entry and HRA object versions are recorded separately.
The originals require Git LFS.

| Reference | Original bytes | Inspected meshes | Scene triangles |
| --- | ---: | ---: | ---: |
| Pelvis, Female, HRA 1.2 | 1,593,336 | 14 | 87,448 |
| Skin, Female, HRA 1.3 | 16,003,176 | 1 | 266,696 |
| Body, Female, HRA 1.5 | 211,624,968 | 888 | 5,557,599 |

## Attribution and authority

Assets are CC BY 4.0, attributed to Kristen Browne and Heidi Schlehlein,
Human Reference Atlas / HuBMAP, from Visible Human data supplied by the National
Library of Medicine. See assets/nih/ATTRIBUTION.md and LICENSE-CC-BY-4.0.txt.
The repository's own Unlicense does not replace the third-party asset license.

This reference assembly is not a measured age-28 average or a complete 206-bone
skeleton. Its skeletal subtree includes pelvic components, lower-limb structures
and vertebrae, including a lumbar-6 label. It includes tissue and cartilage
segmentation. Do not count each mesh as an adult bone or renumber the variant.

Coordinates follow glTF 2.0 Y-up/meters. Bounds are checked from actual vertex
bytes, rather than filename or NIH page counts. Alignment to PHY, joint centers,
mass/inertia, loads, tolerances and manufacturing suitability remain unqualified.
Canonical transforms stay null. Native asymmetry is preserved.

## Offline inspection and optional acquisition

    git lfs pull
    python -m unittest discover -s tests -v
    python tools/audit_assets.py --output /tmp/phy-ref-audits

The standard-library inspector checks chunk lengths, embedded buffers,
supported position/index accessors, finite bounds, index ranges, static hierarchy
and transforms. Unsupported compressed, animated or skinned geometry fails.
It does not certify watertightness, intersections, anatomy or fabrication.

If LFS objects are unavailable, acquisition is explicit:

    python tools/acquire_nih.py --all

Only the three pinned files are acquired, with exact hashes, sizes and public
NIH identifiers. Source changes fail rather than silently upgrading. Existing
non-pointer files are not overwritten. Raw imaging and Blender/FBX bundles are
excluded.

The PR workflow independently acquires, verifies and audits these originals,
then uploads exact objects to this repository's LFS storage. It never pushes
a Git branch or main. Originals are not embedded as text/base64.

## Small comparison previews

assets/nih/derived contains a 19,983-triangle pelvis and a 25,000-triangle skin
preview. Pelvic structures retain source node names. Native world coordinates
and asymmetry are unchanged. Material base colors are retained; normals may be
calculated by the viewer.

    python -m pip install -r requirements-preview.txt
    python tools/build_previews.py --output /tmp/phy-ref-previews

The pinned VTK recipe welds exact duplicate points and performs quadric
decimation. Its manifest records source/output/tool hashes, versions, budgets,
node bounds and sampled distances in both directions. Samples are not a global
Hausdorff bound or landmark qualification. Use original surfaces for engineering
feature studies. The 212 MB assembly is indexed without loading it into Studio
by default.

NASA PDFs remain in PHY under the existing decision. PHY-REF owns NIH binaries,
derivatives and provenance. PHY should pin a reviewed commit and annotate
landmarks before adopting embodiment inputs.
