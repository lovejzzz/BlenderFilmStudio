# RC6 C23 attempt-101 — particle ceiling physical failure

## Result

The one preregistered Preview-96 run completed all 36 Data and Mesh frames and
is retained as a physical `FAIL 23/27`. The independent audit passes 20/20.
This is not a process, resource or evidence failure.

Exact identities:

- execution commit: `f2609a15c481945293b042967609d087444857f7`
- result self hash: `f53d67fe55d46040e75fda5b292514897420461277378710edec306f906fd7ca`
- receipt self hash: `b935d0a139f22680006c56b8efb463d28e7447e818774815317c025845683977`
- independent-audit self hash: `2dd2fa0bbda50ca1c2b99de12513378194429632fed3c52737f3e38ef794b05f`

The four failed physical checks are unchanged by name:

- source-relative volume error exceeds 25%;
- temporal volume drift exceeds 15%;
- positive liquid bodies exceed 16;
- connected components exceed 32.

## Comparison with exact C18

Changing only `particle_maximum 16 → 12` is a material regression:

| Metric | C18 max16 | C23 max12 |
| --- | ---: | ---: |
| maximum source-relative volume error | 47.217227% | 79.780651% |
| maximum temporal volume drift | 33.451408% | 62.866608% |
| first source/temporal failure | frame 25 | frame 24 |
| maximum positive liquid bodies | 37 | 36 |
| first positive-body failure | frame 36 | frame 25 |
| maximum connected components | 37 | 38 |
| first component failure | frame 36 | frame 36 |
| maximum cup-solid intrusion | 0.748564% | 0.993976% |
| fluid Data time | 1404.51 s | 1269.60 s |

The tiny maximum-body change does not compensate for much worse conservation,
earlier fragmentation and increased obstacle intrusion. The faster Data bake
is a cost observation, not a physical success.

## Scope and next gate

The exact R40 trajectory remained within about 5.2 nanometers, significant
solver-owned spill began at frame 24, all 108 cache files were present, and the
run made zero renders, saves, builds, network calls or engine writes. Work and
evidence roots used about 19 MiB and 232 KiB, respectively.

Close `particle_maximum` as a scalar: do not test 14, 10 or another minimum.
Before selecting a different degree of freedom, C24 must perform one fresh,
zero-Blender copied-cache comparison of C23 versus C18 at the Data and Mesh
layers. It must separate onset from maximum severity and retain this immutable
attempt. Rendering remains forbidden.
