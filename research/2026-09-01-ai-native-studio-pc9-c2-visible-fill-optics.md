# PC9 C2 — visible fill optics

PC9 development run-02 closes the C1 physics failure: all three bottles respond and finish near 90 degrees, with zero authored target poses and zero post-release actor pose keys. It is nevertheless retained as a visual failure because the opaque bottle shell hides the internal columns. Colored labels do not prove liquid state and may actively confuse the reading.

C2 changes no fixture byte, physical input, threshold, camera or pose. The product's generic `FILLED_LATHED_BOTTLE` factory may replace the opaque shell shader with native glass and improve the visibility of the already fill-derived internal cylinder and its top surface. Alpha-dither transparency, external fill gauges and encoding the fill in the label are forbidden.

The next development run must still pass all machine criteria and all seven frozen direct visual questions. If the three exact fill heights are not readable at first glance, the run is retained rather than accepted.
