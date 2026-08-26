import json
import os
import socket
import subprocess
from pathlib import Path

import bpy


worker_root = Path(os.environ["BFS_B37_WORKER_ROOT"]).resolve()
control_root = Path(os.environ["BFS_B37_CONTROL_ROOT"]).resolve()
report_path = Path(os.environ["BFS_B37_REPORT_PATH"]).resolve()
allowed_marker = Path(os.environ["BFS_B37_ALLOWED_MARKER"]).resolve()
outside_read_path = Path(os.environ["BFS_B37_OUTSIDE_READ_PATH"]).resolve()
outside_write_path = Path(os.environ["BFS_B37_OUTSIDE_WRITE_PATH"]).resolve()
child_marker = Path(os.environ["BFS_B37_CHILD_MARKER"]).resolve()
loopback_port = int(os.environ["BFS_B37_LOOPBACK_PORT"])
loopback_nonce = os.environ["BFS_B37_LOOPBACK_NONCE"]
fake_secret_expected = "BFS_B37_NONSECRET_ENV_CANARY_V1"

for candidate in (report_path, allowed_marker, child_marker):
    candidate.relative_to(worker_root)
for candidate in (outside_read_path, outside_write_path):
    candidate.relative_to(control_root)


def attempt(label, operation):
    try:
        value = operation()
        return {"success": True, "value": value, "errorType": None, "error": None}
    except Exception as error:  # evidence records the exact local denial surface
        return {
            "success": False,
            "value": None,
            "errorType": type(error).__name__,
            "error": str(error),
            "label": label,
        }


def allowed_write():
    allowed_marker.write_text("B37_ALLOWED_WRITE\n", encoding="utf-8")
    return allowed_marker.is_file()


def outside_read():
    return outside_read_path.read_text(encoding="utf-8").strip()


def outside_write():
    outside_write_path.write_text("B37_OUTSIDE_WRITE\n", encoding="utf-8")
    return outside_write_path.is_file()


def loopback_connect():
    with socket.create_connection(("127.0.0.1", loopback_port), timeout=3.0) as connection:
        connection.sendall((loopback_nonce + "\n").encode("utf-8"))
        return connection.recv(16).decode("utf-8").strip()


def child_exec():
    completed = subprocess.run(
        ["/usr/bin/touch", str(child_marker)],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return {"returnCode": completed.returncode, "markerExists": child_marker.is_file()}


fake_secret_value = os.environ.get("BFS_B37_FAKE_SECRET")
capabilities = {
    "allowedWrite": attempt("allowedWrite", allowed_write),
    "outsideRead": attempt("outsideRead", outside_read),
    "outsideWrite": attempt("outsideWrite", outside_write),
    "loopbackConnect": attempt("loopbackConnect", loopback_connect),
    "childExec": attempt("childExec", child_exec),
    "fakeSecretVisible": {
        "success": fake_secret_value == fake_secret_expected,
        "value": fake_secret_value,
        "errorType": None,
        "error": None,
    },
}
report = {
    "schemaVersion": "bfs.workerContainmentProbe.v0.1",
    "processId": os.getpid(),
    "blenderVersion": bpy.app.version_string,
    "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
    "capabilities": capabilities,
}
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(
    "BFS_B37_PROBE "
    f"pid={report['processId']} "
    + " ".join(f"{key}={value['success']}" for key, value in capabilities.items())
)
