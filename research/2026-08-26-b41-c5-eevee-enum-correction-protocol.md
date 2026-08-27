# B41-C5 · Blender 5.2 Eevee enum correction protocol

Status: preregistered before correction tooling or output.

B41-C4 built and launched the real `linux/amd64` worker. Blender 5.2.0 LTS reported the exact engine enum set `BLENDER_EEVEE`, `BLENDER_WORKBENCH`, `CYCLES` and rejected the canary's `BLENDER_EEVEE_NEXT` assignment before rendering.

B41-C5 changes only that runtime-canary literal to `BLENDER_EEVEE`. The inherited analyzer receives `BLENDER_EEVEE_NEXT` only in its ancestry projection, while the unmodified report must separately record `BLENDER_EEVEE`. The Linux executable hash, image, Dockerfile, launch boundary, 32×32 output gate and forced-timeout contract remain frozen.

The nonfatal missing `/work/tmp` PulseAudio warning is retained as an unresolved observation and is not modified here. Any subsequent failure remains a valid rejection and requires a separate correction.
