# Sacrum–left hemipelvis datum review

`pelvis_left_landmarks.json` is **awaiting independent review**. Five feature
definitions are available; accepted coordinates, calibration, tolerances,
registration and release remain unknown.

## Source and scope

NIH 3DPX-020984 entry 2 / HRA pelvis 1.2 original SHA-256:
`155603d0c44a8ed1e0ca307f1ec3037941304f29f4187631135a9a150fab048d`.
The unchanged native preview SHA-256 is
`c619c5fd8aefb971f9fd036b2f26e5809e0c102ddf8ba37474d33a84c52d9f49`.
Original: 1,593,336 bytes; preview: 373,404 bytes / 19,983 triangles.
Both use source world Y-up coordinates and glTF meters. No centering, height
normalization, mirroring, anatomical orientation or PHY registration is accepted.

Review only `BONE_SACRUM` and one fused adult `BONE_HIP_L`. Six left cortical/
spongy segments form a label crosswalk into one hip identity. The right side and
coccyx remain visual context. Native asymmetry and source display colors remain.

| Candidate | Feature | Original node / cortical label |
| --- | --- | --- |
| L_ASIS | Anterior superior iliac spine | 13 / VH_F_ilium_compact_bone_L |
| L_PSIS | Posterior superior iliac spine | 13 / VH_F_ilium_compact_bone_L |
| L_PUBIC_TUBERCLE | Pubic tubercle | 9 / VH_F_pubis_compact_bone_L |
| L_ISCHIAL_TUBEROSITY | Ischial tuberosity | 20 / VH_F_ischium_compact_bone_L |
| SACRAL_PROMONTORY | Anterior superior sacral rim | 1 / VH_F_sacrum |

Definitions and point-selection questions are paraphrased from OpenStax Anatomy
& Physiology 2e [8.3](https://openstax.org/books/anatomy-and-physiology-2e/pages/8-3-the-pelvic-girdle-and-pelvis)
and [7.3](https://openstax.org/books/anatomy-and-physiology-2e/pages/7-3-the-vertebral-column).
They identify features; they supply no numerical osteometry here.

## Review sequence and gates

1. Use Studio's reduced preview to propose points and views. Export its draft
   JSON with preview face, vertex indices, barycentric weights, native point,
   original node label and source/preview/packet hashes. QEM decimation cannot
   identify the corresponding original face; that field remains null.
2. Run `python tools/validate_landmark_review.py --draft /path/to/draft.json`.
   Reconstruction to 1e-7 meters checks numerical consistency only, not anatomy
   or a machining tolerance.
3. Two independent reviewers annotate the pinned original pelvis, documenting
   identity, original node/primitive/face or surface patch, vertex lineage,
   point-selection rule and native coordinates in several views. The broad
   tuberosity needs a reviewed patch rule; sacral midline needs a reviewed
   median-plane construction.
4. Establish metric calibration and segmentation evidence for this exact source.
   Meter encoding, donor stature and display bounds alone cannot establish it.
   Separate repeatability, segmentation and representation errors. Sampled
   preview errors are neither global bounds nor accepted tolerances.
5. SYSOP approves definitions, numerical error/residual budgets and the review
   decision. Only a later reviewed packet can contain accepted original points.
   Later rigid fitting requires at least four reviewed noncoplanar correspondences,
   a conditioning check and residuals against the approved budget. These five
   features alone do not establish a complete datum frame, hip center,
   sacroiliac contact fit or spinal joint axis.

Stop if a feature or metric fidelity is unresolved, or reviewers disagree beyond
their approved budget. The body assembly's L6 label remains unresolved; do not
assume canonical L5 meets the source sacrum.

NASA HIDH/OCHMO-HB-004 and prior PHY references remain positioning, range,
methodology and operating-condition evidence. They cannot supply missing bone
features or establish compliance. Microgravity observations do not rescale SOPHY;
removing gravity is not tissue or joint qualification.

## Authority and delivery

The packet belongs in PHY-REF. Any accepted embodiment/mechanical change requires
a separate PHY review. SOPHY 1.0.0 height/span 1676.4 mm, all 206 IDs, existing
dimension maps and A0 bearing/stop blockers are unaffected. No dimension maps or
fabrication qualification are added by this review setup.

Assets retain Kristen Browne / Heidi Schlehlein attribution and CC BY 4.0; see
`assets/nih/ATTRIBUTION.md`. Existing original binaries, preview bytes and manifest
are preserved. Software checks verify custody and preview geometry only.
