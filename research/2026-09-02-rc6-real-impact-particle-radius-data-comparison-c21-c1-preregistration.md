# RC6 C21 C1 preregistration — one receipt-hash leaf

Date: 2026-09-02
Status: preregistered before attempt-100 evidence root

Attempt-99's independent audit passes22/23. The sole failure is a transcription
of C19's receipt self hash: the C21 spec says `...5fea41d`; the committed receipt,
its own canonical recomputation and prior state all say `...8a63de`.

C1 is audit-only. It binds the complete 12-file retained attempt-99 evidence
root, proves the original audit's exact one-failure shape, constructs a
corrected in-memory view whose only changed leaf is `baseline.c19ReceiptHash`,
and independently checks the C19 result, receipt and audit. It creates only one
fresh attempt-100 evidence root. No analyzer, cache copy, Blender, bake, render,
save, network call or retained-root write is allowed. The scientific result and
claim ceiling are unchanged.
