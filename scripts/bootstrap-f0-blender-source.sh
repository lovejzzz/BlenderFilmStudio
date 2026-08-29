#!/bin/sh
set -eu

SOURCE_URL="https://projects.blender.org/blender/blender.git"
SOURCE_TAG="v5.2.0"
SOURCE_COMMIT="fbe6228777e7d9afefcd61a413844e790ae75db7"
REQUIRED_FREE_KIB=$((160 * 1024 * 1024))

usage() {
  printf '%s\n' \
    "Usage: $0 --workspace /absolute/path [--execute] [--with-dependencies]" \
    "" \
    "Default mode only prints the pinned source-acquisition plan." \
    "--execute performs the clone after safety and disk checks." \
    "--with-dependencies also runs Blender's official 'make update' step."
}

workspace=""
execute="false"
with_dependencies="false"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --workspace)
      [ "$#" -ge 2 ] || { usage >&2; exit 64; }
      workspace="$2"
      shift 2
      ;;
    --execute)
      execute="true"
      shift
      ;;
    --with-dependencies)
      with_dependencies="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

[ -n "$workspace" ] || { usage >&2; exit 64; }
case "$workspace" in
  /*) ;;
  *) printf 'Workspace must be an absolute path.\n' >&2; exit 64 ;;
esac
[ "$workspace" != "/" ] || { printf 'Workspace may not be filesystem root.\n' >&2; exit 64; }

workspace_parent=$(dirname "$workspace")
[ -d "$workspace_parent" ] || {
  printf 'Workspace parent must already exist: %s\n' "$workspace_parent" >&2
  exit 66
}
workspace_parent=$(cd "$workspace_parent" && pwd -P)
workspace="$workspace_parent/$(basename "$workspace")"

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -n "$repo_root" ]; then
  repo_root=$(cd "$repo_root" && pwd -P)
  case "$workspace/" in
    "$repo_root/"*)
      printf 'Workspace must be outside the BlenderFilmStudio repository: %s\n' "$repo_root" >&2
      exit 65
      ;;
  esac
fi

source_dir="$workspace/blender-v5.2.0-src"
build_dir="$workspace/build-blender-v5.2.0"

if [ -e "$source_dir" ]; then
  printf 'Pinned source target already exists; refusing to overwrite: %s\n' "$source_dir" >&2
  exit 73
fi

free_kib=$(df -Pk "$workspace_parent" | awk 'NR==2 {print $4}')
[ -n "$free_kib" ] || { printf 'Could not measure workspace disk.\n' >&2; exit 74; }

printf '%s\n' \
  "F0 Blender source bootstrap plan" \
  "  upstream: $SOURCE_URL" \
  "  tag: $SOURCE_TAG" \
  "  commit: $SOURCE_COMMIT" \
  "  source: $source_dir" \
  "  expected build root: $build_dir" \
  "  free KiB: $free_kib" \
  "  required KiB: $REQUIRED_FREE_KIB" \
  "  dependencies: $with_dependencies" \
  "  execute: $execute"

if [ "$free_kib" -lt "$REQUIRED_FREE_KIB" ]; then
  printf 'F0_SOURCE_BOOTSTRAP_BLOCKED: insufficient free disk.\n' >&2
  exit 75
fi

if [ "$execute" != "true" ]; then
  printf '%s\n' "F0_SOURCE_BOOTSTRAP_PLAN_ONLY: rerun with --execute after review."
  exit 0
fi

command -v git >/dev/null 2>&1 || { printf 'git is required.\n' >&2; exit 69; }
mkdir -p "$workspace"

git clone --depth 1 --branch "$SOURCE_TAG" --single-branch "$SOURCE_URL" "$source_dir"
observed_commit=$(git -C "$source_dir" rev-parse HEAD)
if [ "$observed_commit" != "$SOURCE_COMMIT" ]; then
  printf 'Pinned source mismatch: expected %s, observed %s\n' "$SOURCE_COMMIT" "$observed_commit" >&2
  exit 76
fi
git -C "$source_dir" checkout --detach "$SOURCE_COMMIT"

if [ "$with_dependencies" = "true" ]; then
  command -v make >/dev/null 2>&1 || { printf 'make is required for dependency acquisition.\n' >&2; exit 69; }
  make -C "$source_dir" update
  observed_after_update=$(git -C "$source_dir" rev-parse HEAD)
  if [ "$observed_after_update" != "$SOURCE_COMMIT" ]; then
    printf 'Dependency update moved source HEAD: expected %s, observed %s\n' "$SOURCE_COMMIT" "$observed_after_update" >&2
    exit 76
  fi
fi

printf '%s\n' \
  "F0_SOURCE_BOOTSTRAP_ACCEPTED" \
  "Pinned source is ready at: $source_dir" \
  "Next: preregister the F0.1 run, perform a fresh disk admission, then follow the official macOS build instructions." \
  "Typical official entry points from the source root are 'make update' and 'make'."
