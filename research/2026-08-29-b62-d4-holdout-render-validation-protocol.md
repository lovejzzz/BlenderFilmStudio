# B62-Q1-D4 holdout render-validation protocol

Date: 2026-08-29  
State: **PREREGISTERED before tool creation**

D3 found one eligible cell without reading frames 193, 204, 228, 252, 276 or 288. D4 now unseals those frames only after an admission receipt binds the parent evidence and frozen tools.

The selected transform is baked into a new camera on every integer frame 193–288 in a derived `.blend`; the original camera remains untouched for paired control renders. A second Blender process renders original and corrected at all six holdouts using the same Cycles CPU settings: 960×540, 16 spp, denoise on, fixed non-animated seed. Each render produces a multilayer EXR, review PNG and decoded pixel report. A third Blender process reopens the derived scene, verifies the bake and independently repeats geometry plus EXR decoding.

The geometry bounds are exactly the D3 engineering template. Every corrected holdout must pass and every original holdout must fail. All 12 EXRs must be finite, non-empty and pairwise different. These rules can admit the mechanical correction, but they cannot judge composition taste. After machine completion the six image pairs must still be viewed and the human observation recorded without rewriting the machine verdict.
