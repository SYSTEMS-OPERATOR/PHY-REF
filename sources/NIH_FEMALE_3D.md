# NIH female 3D geometry acquisition register

Status: candidate inventory; original GLB binaries not yet downloaded, verified, or committed.

Candidates:

| ID | Model | Official entry | Role |
| --- | --- | --- | --- |
| 3DPX-020992 | Female united reference organs | https://3d.nih.gov/entries/3DPX-020992 | multi-organ context, not a validated full skeleton |
| 3DPX-020984 | Female pelvis | https://3d.nih.gov/entries/3DPX-020984 | pelvic comparison |
| 3DPX-020986 | Female skin | https://3d.nih.gov/entries/3DPX-020986 | external envelope comparison |

Before mirroring each file: verify the entry, exact download URL, rights/license, original filename, actual byte size, SHA-256, coordinate units, geometry bounds, object identities, mesh/triangle counts, and whether anatomy matches its label. Record retrieval date and version. Avoid guessing dimensions or license. Prefer regular Git for small binaries and Git LFS for larger ones; do not embed binary files through the text-only GitHub connector.

Use as external references for the PHY Female 28, Female 28 Refined, and SOPHY Scale profiles. Do not promote donor anatomy into canonical geometry or imply these GLBs are a measured 28-year-old population average.

Explicit exclusion: do not mirror the ~40 GB NLM Visible Human Female imaging dataset.

Boundary: PHY-REF stores vetted NIH geometry and derivative tools; PHY owns canonical engineering geometry and directly stored NASA anthropometry documents.
