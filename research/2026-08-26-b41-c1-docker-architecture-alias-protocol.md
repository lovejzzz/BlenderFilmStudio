# B41-C1 · Docker architecture alias correction protocol

Status: preregistered before correction tooling or output.

B41 stopped before download or runtime because Docker's server-version API reports `arm64`, while Colima and the frozen canonical host identity use `aarch64`. B41-C1 changes exactly one operation: normalize raw Docker `arm64` to canonical `aarch64` before comparison and evidence recording.

Every artifact, disk, image, launch, isolation, Eevee, timeout, promotion and audit condition remains byte-for-value or semantically frozen from B41. Any other raw architecture remains a hard failure.
