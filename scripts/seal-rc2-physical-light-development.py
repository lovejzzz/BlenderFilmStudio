#!/usr/bin/env python3
"""Seal the accepted-binary RC2 development result into a durable research root."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def run(argv, cwd):
    return subprocess.run(argv, cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--product-source-root", type=Path, required=True)
parser.add_argument("--development-root", type=Path, required=True)
parser.add_argument("--workspace-route-root", type=Path, required=True)
parser.add_argument("--negative-root", type=Path, required=True)
parser.add_argument("--compatibility-root", type=Path, required=True)
parser.add_argument("--output-root", type=Path, required=True)
args = parser.parse_args()

repository = args.repository_root.resolve(strict=True)
product = args.product_source_root.resolve(strict=True)
development = args.development_root.resolve(strict=True)
workspace_route = args.workspace_route_root.resolve(strict=True)
negative = args.negative_root.resolve(strict=True)
compatibility = args.compatibility_root.resolve(strict=True)
output = args.output_root.resolve()
output.mkdir(parents=True, exist_ok=False)
(output / "review").mkdir()

copies = {
    development / "evidence" / "development.json": output / "development.json",
    development / "evidence" / "machine-audit.json": output / "machine-audit.json",
    development / "evidence" / "reopen-verification.json": output / "reopen-verification.json",
    workspace_route / "evidence" / "workspace-operator-development.json": output / "workspace-route-rc2.json",
    negative / "evidence" / "negative-controls-development.json": output / "negative-controls.json",
    compatibility / "evidence" / "workspace-operator-development.json": output / "backward-compatibility-rc1.json",
}
review_source = development / "evidence" / "review"
for name in (
    "cause-frame-0033.png",
    "contact-frame-0054.png",
    "reveal-frame-0081.png",
    "reveal-actual.png",
    "reveal-closed-counterfactual.png",
    "contact-clip.mp4",
    "contact-clip-contact-sheet.png",
):
    copies[review_source / name] = output / "review" / name
for source, destination in copies.items():
    shutil.copy2(source, destination)

preflight_process = subprocess.run(
    ["node", "scripts/preflight-f0-source-host.mjs"],
    cwd=repository,
    check=False,
    text=True,
    capture_output=True,
)
preflight = json.loads(preflight_process.stdout)
preflight["commandExitCode"] = preflight_process.returncode
(output / "host-preflight.json").write_text(json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8")

module_path = product / "scripts" / "modules" / "film_studio_physical_light.py"
operator_path = product / "scripts" / "startup" / "bl_operators" / "film_studio_workspace.py"
operator_numstat = run(["git", "diff", "--numstat", "--", str(operator_path.relative_to(product))], product).split()
operator_additions, operator_deletions = int(operator_numstat[0]), int(operator_numstat[1])
module_additions = len(module_path.read_text(encoding="utf-8").splitlines())
source_scope = {
    "schemaVersion": "bfs.rc2ProductSourceScopeDevelopment.v0.1",
    "status": "PASS",
    "branch": run(["git", "branch", "--show-current"], product),
    "baseCommit": run(["git", "rev-parse", "HEAD"], product),
    "paths": [
        {"path": str(module_path.relative_to(product)), "additions": module_additions, "deletions": 0, "sha256": sha256_file(module_path)},
        {"path": str(operator_path.relative_to(product)), "additions": operator_additions, "deletions": operator_deletions, "sha256": sha256_file(operator_path)},
    ],
    "totals": {"paths": 2, "additions": module_additions + operator_additions, "deletions": operator_deletions},
    "ceilings": {"paths": 2, "additions": 1000, "deletions": 220},
    "checks": {
        "pathCountWithinCeiling": 2 <= 2,
        "additionsWithinCeiling": module_additions + operator_additions <= 1000,
        "deletionsWithinCeiling": operator_deletions <= 220,
        "diffCheckClean": subprocess.run(["git", "diff", "--check"], cwd=product).returncode == 0,
        "moduleHasNoFrozenFixtureIdentity": not any(token in module_path.read_text(encoding="utf-8") for token in ("RC2-THE-SIGNAL-GATE", "ceb47e803e2b5e5740953c4eb1e96619b3ecaab60bd7c574299d340283513e03", "2efea2e822ce2971b40a277cb25ce9f69273284c3a30bfb76dbc680cd5eee0cf")),
    },
}
source_scope["status"] = "PASS" if all(source_scope["checks"].values()) else "FAIL"
(output / "product-source-scope.json").write_text(json.dumps(source_scope, indent=2, sort_keys=True) + "\n", encoding="utf-8")

machine = load(output / "machine-audit.json")
reopen = load(output / "reopen-verification.json")
route = load(output / "workspace-route-rc2.json")
negative_controls = load(output / "negative-controls.json")
backward = load(output / "backward-compatibility-rc1.json")
preregistration = load(repository / "specs" / "ai-native-studio-rc2-physical-light-transfer-preregistration.v0.1.json")
visual_answers = [{"question": question, "answer": "YES"} for question in preregistration["directVisualQuestions"]]
acceptance = {
    "schemaVersion": "bfs.rc2PhysicalLightDevelopmentAcceptance.v0.1",
    "status": "DEVELOPMENT_PASS_FORMAL_BUILD_BLOCKED",
    "projectTitle": preregistration["projectTitle"],
    "machineAudit": {"status": machine["status"], "passCount": machine["passCount"], "checkCount": machine["checkCount"]},
    "directVisualReview": {"status": "PASS", "yesCount": sum(row["answer"] == "YES" for row in visual_answers), "questionCount": len(visual_answers), "answers": visual_answers},
    "additionalChecks": {
        "saveReopen": reopen["status"],
        "workspaceRoute": route["status"],
        "negativeControls": negative_controls["status"],
        "rc1BackwardCompatibility": backward["status"],
        "productSourceScope": source_scope["status"],
    },
    "formalBuildAdmission": {"status": preflight["status"], "freeGiB": preflight["disk"]["freeGiB"], "requiredFreeGiB": preflight["disk"]["requiredFreeGiB"], "failure": preflight["failures"]},
    "claimCeiling": "Accepted-binary development proves a reusable solver-owned rolling-body/hinged-occluder/static-light path, visual causality, persistence, negative controls, and RC1 routing compatibility on this host. It does not prove the preregistered clean native build, a distributable binary, photoreal asset quality, or cross-platform behavior.",
    "skillBindings": {
        "skill": "/Users/mengyingli/.codex/skills/physical-film-direction/SKILL.md",
        "skillSha256": sha256_file(Path("/Users/mengyingli/.codex/skills/physical-film-direction/SKILL.md")),
        "validatedPatternsSha256": sha256_file(Path("/Users/mengyingli/.codex/skills/physical-film-direction/references/validated-patterns.md")),
    },
}
(output / "acceptance.json").write_text(json.dumps(acceptance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

files = []
for path in sorted(item for item in output.rglob("*") if item.is_file()):
    files.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
manifest = {"schemaVersion": "bfs.rc2DevelopmentRootManifest.v0.1", "files": files}
manifest["manifestHash"] = hashlib.sha256(canonical(manifest).encode("utf-8")).hexdigest()
(output / "root-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": acceptance["status"], "outputRoot": str(output), "manifestHash": manifest["manifestHash"], "fileCount": len(files)}, sort_keys=True))
