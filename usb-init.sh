#!/usr/bin/env bash
# =============================================================================
# usb-init.sh — USBAGENT v4.1 Context Injector
# Hard-blocker: Forces Gemini CLI to read all state files before any action.
# Usage: source usb-init.sh   OR   eval "$(./usb-init.sh)"
# =============================================================================

set -euo pipefail

FILES=(
  "GEMINI.md"
  "SESSION_STATE.md"
  "ARCHITECTURE.md"
  "CONVENTIONS.md"
)

MISSING=()
for f in "${FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    MISSING+=("$f")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "❌ ERROR: The following required context files are missing:" >&2
  for m in "${MISSING[@]}"; do
    echo "   - $m" >&2
  done
  exit 1
fi

echo "================================================================="
echo "  USBAGENT v4.1 — EXPERT MODE INIT"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================="
echo ""
echo "⚠️  HARD-BLOCKER ACTIVE: You MUST read all context below before"
echo "   forming any plan, writing any code, or making any assumption."
echo "   Do NOT rely on prior session memory. Ground truth is below."
echo "================================================================="
echo ""

for f in "${FILES[@]}"; do
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📄 FILE: $f"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  cat "$f"
  echo ""
done

echo "================================================================="
echo "✅ CONTEXT LOAD COMPLETE."
echo "   You are now operating as USBAGENT Expert v4.1."
echo "   Current task and blockers are defined in SESSION_STATE.md."
echo "   Follow CONVENTIONS.md strictly. Follow ARCHITECTURE.md strictly."
echo "   DO NOT hallucinate file contents, tool states, or task status."
echo "   Your FIRST response must acknowledge the current task and"
echo "   blockers from SESSION_STATE.md before doing anything else."
echo "================================================================="
