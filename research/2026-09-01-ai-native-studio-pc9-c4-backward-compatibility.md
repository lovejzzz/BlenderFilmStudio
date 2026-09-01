# PC9 C4 — exact backward compatibility

The PC9 development module passed 29 authority attacks and retained exact PC8 Bullet physics, initial conditions and pose provenance. A stricter comparison found a small but real PC8 measured-shutter drift. Running the same comparison with the accepted PC8 module passed exactly, so the harness is not the source.

The cause is a 0.0002 m change in the old actor seam's major-radius offset introduced while scaling basketball seams for metric v0.5. Actor detail geometry participates in narrative camera fitting. The camera therefore moved slightly and changed projected motion, even though Bullet stayed exact.

C4 authorizes one compatibility restoration: v0.1/v0.2/v0.4 keep the historical `radius + 0.002` seam, while v0.5 keeps radius-scaled seams. No fixture, physical value, threshold, camera algorithm or pose authority changes.
