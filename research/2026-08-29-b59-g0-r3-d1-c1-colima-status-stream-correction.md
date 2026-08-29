# B59-G0-R3-D1-C1 · Colima status stream correction

Date: 2026-08-29
Status: PREREGISTERED — implementation not yet changed
Formal D1 root at registration: absent

The first shortened rehearsal passed timing, tracked-file identity, evidence, read-only accounting and 10/10 attacks, but failed `COLIMA_RUNTIME_CONTINUITY`. Colima was actually running; its CLI wrote status lines to stderr while the tool parsed stdout only. Independent live replay failed for the same reason.

- `results.json` SHA-256: `c17192893f8d6512c7d918b22b0c140542d2ba03b8dfc21dd208ce617d4ddbd8`
- `audit.json` SHA-256: `f9e80314c6aa8a84cb3cfd22909f0f8acfcea936a79fcbcb032c244e13221891`
- Rehearsal spec SHA-256: `fc65ad8aec42645bbe440454b7d822c792f2d0aaabc533294274bfe2ed52be26`
- Base formal spec SHA-256: `079ea4a876fdcbbc40fb09baf0780341689af103fd18d4ffce83ae3035f4850a`

C1 uses a bounded process API that concatenates captured stdout and stderr and rejects non-zero exit. It applies only to the fixed Colima status call in runner and auditor. Docker output handling, sample fields, gates, mutations and attribution rules do not change. A second shortened rehearsal must pass 8/8 gates and 10/10 attacks before formal D1 starts.
