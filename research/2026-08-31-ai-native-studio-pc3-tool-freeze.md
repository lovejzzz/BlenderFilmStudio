# PC.3 integrated render tool freeze

The exact 288-frame renderer, reopen semantic/pixel auditor, video runner and independent machine auditor are frozen before formal root creation. Each product render writes one temporary multilayer EXR, extracts one finite Combined RGBA image to PNG and immediately removes the EXR. The second Blender start performs no render; it compares all 288 B frames with accepted PB.6 A and verifies accepted PC.2 identity. FFmpeg and FFprobe binaries are exact-hash bound. Human review remains closed until the machine root is sealed.
