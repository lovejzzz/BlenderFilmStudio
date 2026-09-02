# RC6 cached FLIP particle axis C1 attempt-34 result

Attempt-34 is an execution and independent-audit `PASS`. It reused the exact
resolution-192, seven-frame, radius-9.0 candidate through a complete fresh
copy, exposed its already-enabled FLIP particle system in memory, and performed
zero data bakes, mesh bakes, saves, renders, network calls or engine writes.
The independent audit passed 27/27 with self hash
`bfd71c7b18e30cdfea8d5a2b7196da27a72d445dd104ea0b744da2d10322ed56`.

The physical diagnosis is narrow but decisive:

- Frames 1–3 contain zero particles outside either the raw cup interior or the
  one-base-voxel expanded interior.
- Frames 4–7 contain exactly nine below-floor particles and zero radial-wall or
  above-rim particles. At frame 7 this is 9 of 107,825 particles, or
  `0.00008347`.
- The below-floor particle minimum is fixed at cup-local
  `z=-0.18023688 m`, which is 20.23688 mm below the measured interior floor and
  17.63271 mm beyond the one-voxel floor envelope.
- The bound surface diagnosis at the same peak frame reported 7,814 of 101,808
  mesh vertices below the one-voxel floor envelope, or `0.07675232`, with zero
  radial and above-rim violations.

Therefore the surface failure is not entirely synthetic: a very small cached
particle leak exists. However, surface reconstruction expands nine persistent
particle outliers into 7,814 outside mesh vertices—roughly three orders of
magnitude more classified elements and a visually much larger defect. Further
concavity or radius tuning cannot repair the physical outliers without the
already measured volume/fragmentation tradeoff. The next physical experiment
must localize these nine particles and test the cup effector/collision
representation before any slow tip or impact bake.

This result does not prove a fix, acceptable liquid motion, slow-tip behavior,
impact behavior, visual quality or finished-film quality.
