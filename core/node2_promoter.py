"""
node2_promoter.py  –  Slice 1 / Revision 1.2
Pre-flight checks only.  No git apply, no git commit, no promotion.
Exit 0 → Pre-flight OK.
Exit 1 → Pre-flight FAILED (receipt written with error_log).
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_of_string(text: str) -> str:
    """Normalise to UTF-8 + LF, return hex digest."""
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def _git(args: list[str], repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )


def _current_head(repo: Path) -> str:
    result = _git(["rev-parse", "HEAD"], repo)
    if result.returncode != 0:
        raise RuntimeError(f"git rev-parse HEAD failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _current_branch(repo: Path) -> str:
    result = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    if result.returncode != 0:
        raise RuntimeError(f"git rev-parse --abbrev-ref HEAD failed: {result.stderr.strip()}")
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

def _preflight(request: dict[str, Any], repo: Path) -> list[str]:
    """
    Run all pre-flight checks.
    Returns a list of error strings (empty → all checks passed).
    """
    errors: list[str] = []

    # --- Required fields present ---
    required_fields = [
        "expected_base_commit",
        "approved_diff_contents",
        "execution_result_id",
        "target_branch",
    ]
    for field in required_fields:
        if field not in request:
            errors.append(f"Missing required field: {field}")

    if errors:
        # Cannot proceed with structural checks if fields are missing
        return errors

    expected_base: str = request["expected_base_commit"].strip()
    approved_diff: str = request["approved_diff_contents"]
    target_branch: str = request["target_branch"].strip()

    # --- Repo exists and is a git repo ---
    if not (repo / ".git").exists():
        errors.append(f"Not a git repository: {repo}")
        return errors

    # --- HEAD matches expected_base_commit ---
    try:
        head = _current_head(repo)
    except RuntimeError as exc:
        errors.append(str(exc))
        return errors

    if head != expected_base:
        errors.append(
            f"HEAD mismatch: expected {expected_base!r}, got {head!r}"
        )

    # --- Current branch matches target_branch ---
    try:
        branch = _current_branch(repo)
    except RuntimeError as exc:
        errors.append(str(exc))
        return errors

    if branch != target_branch:
        errors.append(
            f"Branch mismatch: expected {target_branch!r}, current branch is {branch!r}"
        )

    # --- approved_diff_contents is non-empty ---
    if not approved_diff or not approved_diff.strip():
        errors.append("approved_diff_contents is empty")

    return errors


# ---------------------------------------------------------------------------
# Receipt writer
# ---------------------------------------------------------------------------

def _write_receipt(
    receipt_path: Path,
    *,
    success: bool,
    request: dict[str, Any],
    pre_promotion_head: str,
    error_log: list[str],
) -> None:
    receipt: dict[str, Any] = {
        "success": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "execution_result_id": request.get("execution_result_id"),
        "target_branch": request.get("target_branch"),
        "pre_promotion_head": pre_promotion_head,
        "rollback_performed": False,
        "error_log": error_log,
        "metadata": request.get("metadata", {}),
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="node2_promoter – Slice 1 pre-flight only"
    )
    parser.add_argument(
        "--request",
        required=True,
        help="Path to the promotion request JSON file",
    )
    parser.add_argument(
        "--receipt",
        required=True,
        help="Path where the receipt JSON will be written",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the git repository root (default: .)",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    request_path = Path(args.request)
    receipt_path = Path(args.receipt)

    # --- Load request ---
    if not request_path.exists():
        print(f"ERROR: request file not found: {request_path}", file=sys.stderr)
        return 1

    try:
        request: dict[str, Any] = json.loads(
            request_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in request file: {exc}", file=sys.stderr)
        return 1

    # --- Acquire exclusive lock ---
    lock_path = repo / ".git" / "safe_promotion.lock"
    try:
        lock_fd = open(lock_path, "w", encoding="utf-8")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("ERROR: another promotion is in progress (lock held)", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: cannot acquire lock {lock_path}: {exc}", file=sys.stderr)
        return 1

    try:
        # --- Capture HEAD before anything else ---
        try:
            pre_promotion_head = _current_head(repo)
        except RuntimeError as exc:
            pre_promotion_head = "unknown"
            _write_receipt(
                receipt_path,
                success=False,
                request=request,
                pre_promotion_head=pre_promotion_head,
                error_log=[str(exc)],
            )
            print(f"Pre-flight FAILED: {exc}", file=sys.stderr)
            return 1

        # --- Run pre-flight checks ---
        errors = _preflight(request, repo)

        if errors:
            _write_receipt(
                receipt_path,
                success=False,
                request=request,
                pre_promotion_head=pre_promotion_head,
                error_log=errors,
            )
            for err in errors:
                print(f"Pre-flight FAILED: {err}", file=sys.stderr)
            return 1

        # --- All checks passed ---
        # Slice 1 boundary: no git apply, no git commit, no promotion.
        print("Pre-flight OK")
        return 0

    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    sys.exit(main())
