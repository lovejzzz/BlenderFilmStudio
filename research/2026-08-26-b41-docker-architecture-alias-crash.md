# B41 · Docker architecture alias crash before runtime

Status: `NO_RESULT_DOCKER_ARCHITECTURE_ALIAS_CRASH`  
Runtime operations: `0`

The disk guard passed with `134689046528` bytes available and `113214210048` bytes after the frozen 20 GiB projection. The frozen runner then queried the explicitly bound Colima socket with Docker's server-version JSON and compared `Server.Arch` directly to the preregistered Colima/Docker canonical architecture string.

Docker returned `"Arch":"arm64"`; the frozen protocol used `"aarch64"`. These are aliases for the same architecture in the two tools, but the runner had no preregistered normalization rule and threw `B41 Docker server architecture differs`.

The exception happened before the experiment output directory, temporary build root or archive was created. No archive download, Docker build, image, container or Blender process occurred.

B41-C1 must be separately preregistered and may change only architecture normalization: Docker API `arm64` maps to the frozen canonical `aarch64`. It may not change artifact, image, containment, render, timeout, disk or decision gates.
