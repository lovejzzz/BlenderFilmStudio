import json
import os
import signal
import time
from pathlib import Path

output_root = Path(os.environ["BFS_OUTPUT_ROOT"])
output_root.mkdir(parents=True, exist_ok=True)


def ignored(signum, _frame):
    record = {"signal": signum, "ignored": True, "monotonic": time.monotonic()}
    (output_root / "sigterm-observed.json").write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")


signal.signal(signal.SIGTERM, ignored)
(output_root / "timeout-ready.json").write_text(json.dumps({
    "schemaVersion": "bfs.timeoutCanaryReady.v0.1",
    "jobId": os.environ["BFS_JOB_ID"],
    "pid": os.getpid(),
    "sigtermIgnored": True,
}, sort_keys=True) + "\n", encoding="utf-8")
print("BFS_B41_TIMEOUT_CANARY=READY", flush=True)
while True:
    time.sleep(1)
