# B59-G0-R5-C1 · RunAtLoad-only installation correction

Date: 2026-08-29
Status: PREREGISTERED — FRESH V0.2 ROOTS ABSENT
Parent commit: `a4254c22af54f1591dd877273fb1ac4c0936a779`

## Counterexample

R5 v0.1 successfully bootstrapped the exact user LaunchAgent, and `RunAtLoad` produced a valid `HEALTHY` sample. The installer then issued an additional `launchctl kickstart -k` and treated its 10-second timeout as failure. Rollback correctly removed the service and plist while retaining evidence.

Local `launchctl` documentation defines `bootstrap` as loading the service definition and `kickstart` as a separate request to run it immediately regardless of configured launch conditions. The live sample proves that bootstrap honored `RunAtLoad`; a second forced start is redundant and increases installation race surface.

## Single correction

C1 changes initial triggering from `bootstrap + RunAtLoad + kickstart -k` to `bootstrap + RunAtLoad` only. The installer waits up to 30 seconds for a fresh sample whose modification time follows bootstrap, then verifies the loaded service. Its action receipt must record `bootstrapCalls=1` and `kickstartCalls=0`.

All classifier thresholds, 15-minute schedule, 48-hour bounded history, state-file ceilings, notification rule, exact label/runtime/plist, reversible uninstall, zero automatic cleanup/deletion/restart policy, required gates and 15 registered attacks remain unchanged.

The attempt uses fresh roots:

- formal: `experiments/host-capacity-sentinel-v0-2`
- state: `/Users/tianxing/.local/state/BlenderFilmStudio/capacity-sentinel-v0-2`

The retained v0.1 state and formal evidence are read-only parents and are not reused. Passing C1 admits the installed warning mechanism only; long-term retention and Gate 0 closeout remain separate.
