# RC6 Final liquid effector Data comparison accepted

The frozen resolution-192, seven-frame, Data-only comparison completed in
1,349.955457 seconds on the admitted M2 Max. Blender sustained roughly eleven
CPU cores and approximately 2.9–3.3 GB resident memory during observation;
there was no process error, render, Mesh bake, save, network call or engine
remote write. This confirms that roughly three to four minutes per Final-tier
liquid frame is current pipeline cost, not evidence of a failed host.

The immutable accepted baseline used cup effector `surface_distance=1.5` cells
and contained exactly nine `ALIVE` FLIP particles embedded in the modeled cup
floor on frames 4–7. The single candidate changed only that effector distance
to `2.5` cells at the same resolution, physics identity, geometry, placement,
frame window and Data stage. All seven candidate frames had zero strict and
zero one-cell-envelope particle outliers. Candidate result self hash:
`614142061ef4f56f7c08d0bc64cb6a2fca17bf4a2de69634d92c1d32ff7d3795`.

The receipt verdict is `PASS_FINAL_SURFACE_DISTANCE_DATA_SIGNAL`, self hash
`55121a99aa6066eaa625586a77aeb241d727415090c89b02882bd2defb602d8a`.
The independent audit passed 19/19 with self hash
`80693f16740ba776635305892924b34d84c35d1f3316b9f8ac0351e742f68158`.
The work root used 14,882,386 bytes and the evidence root remained below 64
MiB. The exact 14-file cache roster contains one config and one Data file for
each frame 1–7.

This is a causal obstacle-level-set correction signal only. It does not yet
prove reconstructed-surface quality, volume retention, signed topology,
visible cup containment, slow tip, impact or finished-film quality. The next
gate must copy or bind this immutable Data cache without recomputing it, run
Mesh-only reconstruction with the retained resolution-192 surface candidate,
and independently audit every frame against the frozen source volume and cup
interior before any slow-tip experiment.
