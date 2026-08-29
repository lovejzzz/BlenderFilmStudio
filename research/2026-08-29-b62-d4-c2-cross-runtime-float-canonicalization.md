# B62-Q1-D4-C2 cross-runtime float canonicalization

The v0.2 builder passed and created a derived scene, but Node rejected its Python self-hash because Python and ECMAScript spell small decimal exponents differently. C2 freezes a language-independent hash representation for non-integral numbers: exact IEEE-754 binary64 bits encoded as 16 big-endian lowercase hex digits. Persisted observations remain numeric. No render occurred, and no camera or holdout rule changes.
