# RC2 clean-build admission cleanup pass

Date: 2026-09-01

RC2 clean native build admission now passes at 165 GiB free against the frozen
160 GiB conservative threshold. No retained experiment root, source checkout,
personal document or recording was removed.

Attempt-01 removed an exact 17-path allowlist totaling 31.77 GB observed. It
included a 14 GiB old `bud-recorder` Qwen model whose non-metadata files were
verified byte-for-byte and SHA-256 exact against the retained current
`BudRecorder` copy, plus only regenerable package, model, application, Xcode and
simulator caches. Chrome and Spotify caches were excluded because those apps
were running. The attempt correctly remained below the rounded threshold at
159 GiB and is retained as `FAIL_CLEANUP_INSUFFICIENT`.

Attempt-02 removed one additional regenerable, inactive 6.0 GiB Claude VM
bundle and reached 165 GiB with `F0_HOST_PREFLIGHT_ACCEPTED` and no failures.
Its wrapper expected the wrong success spelling and is retained as a harness
failure. C2 attempt-03 performed no mutation, cross-bound both earlier receipts
and accepted the actual preflight status. The accepted receipt is
`experiments/physical-light-transfer/RC2-2026-09-01-build-admission-cleanup-attempt-03/receipt.json`.

The removed caches are not recoverable from Trash, but their documented
recovery class is redownload or regeneration by the owning application. The
formal RC2 work/evidence roots remained absent throughout cleanup.
