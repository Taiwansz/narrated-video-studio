#!/usr/bin/env bash
set -euo pipefail

SCOPE="${1:-local}"
TARGET_PROJECT="${2:-$(pwd)}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_SOURCE="${REPO_ROOT}/.agents/skills/narrated-video-studio"

if [ ! -f "${SKILL_SOURCE}/SKILL.md" ]; then
  echo "Skill source not found at: ${SKILL_SOURCE}" >&2
  exit 1
fi

if [ "${SCOPE}" = "local" ]; then
  TARGETS=(
    "${TARGET_PROJECT}/.agents/skills/narrated-video-studio"
    "${TARGET_PROJECT}/.claude/skills/narrated-video-studio"
  )
else
  TARGETS=(
    "${HOME}/.agents/skills/narrated-video-studio"
    "${HOME}/.claude/skills/narrated-video-studio"
    "${HOME}/.gemini/config/skills/narrated-video-studio"
  )
fi

for T in "${TARGETS[@]}"; do
  mkdir -p "${T}"
  cp -R "${SKILL_SOURCE}/." "${T}/"
  echo "Installed narrated-video-studio skill to: ${T}"
done
