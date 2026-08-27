# B42-C1 · Nested mountpoint correction protocol

B42-C1 changes only the two defects observed in B42: `/repo/worker-output` exists before OCI applies the nested writable bind, and analysis records failed launches instead of throwing on a null observation. Its results use a new directory and cannot overwrite B42 evidence.

The exact B42 image, inputs, benchmarks, four clean builds, tampered-plan control, isolation, timeouts, acceptance gates and non-claims remain frozen. A pass is valid only if the independently generated plans retain their frozen identities, all four Blender compilations complete, both clean builds per benchmark reproduce the expected canonical structure hash, and the fifth container rejects the tampered hash.
