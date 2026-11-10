# Sleeping Pikachu v4: soft plush fur

Script: `scripts/pikachu_v4.py`. Result: `results/pikachu-v4/`. Look mocks: `results/pikachu-v4-mocks/`.
The user picked look A from four mocks, then asked for better ears and fewer sharp edges.
`approved-preview.png` is the quick still the user approved before the full render.

## Changes from v3

1. Even quad body: the SDF mesh is voxel-remeshed (0.011) and relaxed. The decimated sliver triangles that looked jaggy are gone.
2. Soft fur: particle hair on the body and tail, with separate yellow, ink, brown, and red systems driven by the painted masks. The fur is shorter around the muzzle and clears around the face lines.
3. Ears: one leaf-shaped surface per ear, slim at the base, widest near 40%, with a rounded tip.
4. Face turned further toward the camera (54°). Eyes are tapered lines.
5. Tail: thicker, with softened zig-zag corners and its own fur.
6. Color: skin and fur share the same yellow, so gaps do not read orange.
7. Bug fix: a fractional power of a slightly negative sine at the ear tips made NaN values. They became thin strings in the mesh. The value is clamped, and the script now fails on any non-finite SDF value.

Options: `--variant A|B|C|D`, `--ears leaf|upright|droop`, `--no-fur`, `--closeup`.

## Render

108 frames at 1440 × 1080, 128 samples, split over four RTX PRO 6000 pods. See `run-record.json`.
`scripts/finalize_pikachu_v4.sh` merges the frames, verifies the GLB, encodes, and writes checksums.
The GLB has the rig, animation, and painted colors. Particle fur does not export to glTF.
All pods were deleted after the checksums matched. Approximate cost: $3.82.
