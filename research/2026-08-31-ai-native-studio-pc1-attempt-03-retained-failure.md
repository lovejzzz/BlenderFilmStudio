# PC.1 attempt-03 retained scientific-notation audit failure

C3 again completed and semantically passed the exact 26-detail, three-material, six-render product result. Integer-float normalization worked, but the final Node auditor still differed from Python on scientific notation (`8e-08` versus `8e-8`). Python independently validates the build hash. Attempt-03 remains FAIL and will be sealed.

C4 is auditor-only: reproduce Python finite-number spelling, including exponent zero padding, prove the canonicalizer against retained attempt-03, then use fresh attempt-04. Product builder, scene, images, thresholds and operation ceilings must not change.
