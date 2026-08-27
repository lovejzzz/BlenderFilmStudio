# B41-C4 · Platform-specific Blender identity correction protocol

Status: preregistered before correction tooling or output.

B41-C3 proved the Colima guest buildx path reaches true amd64 layers and authenticates the official archive, then stopped because it compared the extracted Linux executable with the historical local macOS hash. B41-D1-C1 has now independently derived and audited the Linux member as `174666336` bytes with SHA-256 `83e8261eace07a5337f71b52d156c1eece1a6ba913403cc6406182ae58bacf27`.

B41-C4 changes the two executable-hash literals in the Dockerfile and runtime canary to that derived Linux value. The inherited analyzer receives a projection using its historical macOS field only for ancestry replay, while the unmodified observed runtime report must separately equal the Linux hash. The historical macOS evidence is not edited.

The independent audit may treat absent runtime artifacts as `{}` only for a failed pre-runtime receipt; any successful claim still requires an independently observed valid 32×32 PNG and nonempty `.blend`. Every other build, containment, render, timeout and cleanup condition remains frozen.
