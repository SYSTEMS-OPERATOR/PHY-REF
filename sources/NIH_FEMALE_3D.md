# NIH female 3D geometry acquisition register

Status: three original input GLBs acquired on 2026-10-12 and independently
checked for bytes, SHA-256, static GLB structure, scene counts, bounds and labels.
Anatomical/canonical registration and physical qualification remain open.

Machine catalog: reference_assets.json. Published identifiers, attribution and
license evidence: NIH_entry_evidence.json. Original files are retained through
Git LFS in assets/nih/originals. Pelvic and skin previews are separate derivatives.

| Entry | Original file | HRA object version | NIH entry version |
| --- | --- | --- | --- |
| 3DPX-020984 | VH_F_Pelvis.glb | 1.2 | 2 |
| 3DPX-020986 | 3d-vh-f-skin.glb | 1.3 | 3 |
| 3DPX-020992 | 3d-vh-f-united.glb | 1.5 | 2 |

NIH metadata declares CC-BY and its license hyperlink specifies CC BY 4.0.
Creators and citations are retained in assets/nih/ATTRIBUTION.md. Input files
are not substituted with regenerated outputs. Acquisition uses NIH /api/download;
raw S3 URLs are provenance because direct S3 access is denied.

The full-body audit sums 888 meshes / 5,557,599 triangles. NIH input metadata
reports 16,724 polygons / 8,362 vertices; its unverified aggregate scope cannot
replace the scene audit. Pelvis has 87,448 triangles across fourteen meshes,
versus metadata reporting 2,296 polygons.

The assembly includes a lumbar-6 label and tissue components, not a complete
canonical adult inventory. Review segmentation/anatomy before mapping to PHY.
Preserve asymmetry. These are not age-28 averages, joint centers, interface datums
or validated tissue mechanics.

No raw approximately 40 GB Visible Human Female imaging is acquired. NASA
PDFs remain in PHY. NIH originals, derivatives and provenance belong here.
