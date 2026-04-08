"""
node2_promoter.py  –  Slice 2.4 / Revision 2.4
Safe Promotion Promoter: Implementation of Slice 2 (Apply, Verify, Recovery).
Exit 0 → Process reached a defined outcome state (Receipt generated where applicable).
Exit 1 → Critical systemic failure before or during execution context setup.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
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

def _get_staged_index_hash(repo: Path) -> str:
    """Return the SHA of the current index tree."""
    res = subprocess.run(["git", "write-tree"], cwd=str(repo), capture_output=True, text=True)
    if res.returncode != 0:
        return "unknown"
    return res.stdout.strip()



def _run_safety_rails(repo: Path, affected_files: list[str]) -> tuple[str, list]:
    """Run 3 levels of safety rails and return (status, details)."""
    import subprocess
    details = []
    overall_status = "pass"
    
    # Level 1: Syntax Check
    for f_path in affected_files:
        full_path = repo / f_path
        if full_path.suffix == ".py":
            res = subprocess.run(["python3", "-m", "py_compile", str(full_path)], capture_output=True, text=True)
            details.append({
                "rail_name": f"Syntax: {f_path}",
                "result": "pass" if res.returncode == 0 else "fail",
                "exit_code": res.returncode,
                "log_excerpt": res.stderr if res.returncode != 0 else ""
            })
            if res.returncode != 0: overall_status = "fail"

    # Level 2: Import Check (Base baseline integrity)
    res = subprocess.run(["python3", "-c", "import main"], cwd=str(repo), capture_output=True, text=True)
    details.append({
        "rail_name": "Baseline Integrity (Import main)",
        "result": "pass" if res.returncode == 0 else "fail",
        "exit_code": res.returncode,
        "log_excerpt": res.stderr if res.returncode != 0 else ""
    })
    if res.returncode != 0: overall_status = "fail"

    return overall_status, details

def _rollback(repo: Path, anchor: str) -> bool:
    """Attempt to return repo to a clean state at anchor."""
    try:
        # Reset index and working tree
        subprocess.run(["git", "reset", "--hard", anchor], cwd=str(repo), capture_output=True)
        # Clean untracked files
        subprocess.run(["git", "clean", "-fd"], cwd=str(repo), capture_output=True)
        # Verify if really clean
        res = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo), capture_output=True, text=True)
        return not bool(res.stdout.strip())
    except Exception:
        return False

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
        "approved_diff_hash",
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

    # --- Dirty-repo check ---
    status_result = _git(["status", "--porcelain"], repo)
    if status_result.returncode != 0:
        errors.append(
            f"dirty_repo: git status --porcelain failed: {status_result.stderr.strip()}"
        )
    elif status_result.stdout.strip():
        errors.append(
            "dirty_repo: working tree has uncommitted changes"
        )

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
    outcome_code: str,
    request: dict[str, Any],
    pre_promotion_head: str,
    error_log: str = "",
    apply_started: bool = False,
    apply_completed: bool = False,
    irreversible_action_occurred: bool = False,
    apply_authorized: bool = False,
    rollback_attempted: bool = False,
    rollback_result: str = "not_needed",
    dirty_state_detected: bool = False,
    verification_status: str = "not_ran",
    verification_details: list = None,
    staged_index_hash: str = None,
    started_at: str = None,
) -> None:
    from datetime import datetime, timezone
    approved_diff = request.get("approved_diff_contents") or ""
    source_hash = request.get("approved_diff_hash") or _sha256_of_string(approved_diff)
    
    receipt = {
        "receipt_schema_version": "2.1",
        "outcome_code": outcome_code,
        "request_id": str(request.get("request_id", "unknown")),
        "apply_authorized": apply_authorized,
        "apply_started": apply_started,
        "apply_completed": apply_completed,
        "irreversible_action_occurred": irreversible_action_occurred,
        "rollback_attempted": rollback_attempted,
        "rollback_result": rollback_result,
        "dirty_state_detected": dirty_state_detected,
        "human_gate_required": outcome_code == "S2_VERIFIED_HUMAN_GATE_REQUIRED",
        "safe_to_retry": outcome_code in ["S2_APPLY_NOT_STARTED", "S2_APPLY_FAILED_ROLLBACK_CLEAN", "S2_POSTCHECK_FAILED_ROLLBACK_CLEAN"],
        "eligible_for_promotion_review": outcome_code == "S2_VERIFIED_HUMAN_GATE_REQUIRED",
        "audit_required": "DIRTY" in outcome_code or outcome_code == "S2_BLOCKED_AUDIT_REQUIRED",
        "artifact_identity": {
            "source_hash": source_hash,
            "staged_index_hash": staged_index_hash
        },
        "verification_summary": {
            "status": verification_status,
            "details": verification_details or []
        },
        "execution_timestamps": {
            "started_at": started_at or datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat()
        }
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
    started_at = datetime.now(timezone.utc).isoformat()

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
        _write_receipt(
            receipt_path,
            outcome_code="S2_APPLY_NOT_STARTED",
            request=request,
            apply_authorized=False,
            pre_promotion_head="unknown",
            error_log="lock_contention: another promotion is in progress",
        )
        return 0
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
                outcome_code="S2_APPLY_NOT_STARTED",
                request=request,
                apply_authorized=False,
                pre_promotion_head=pre_promotion_head,
                error_log=str(exc),
                started_at=started_at
            )
            print(f"Pre-flight FAILED: {exc}", file=sys.stderr)
            return 0

        # --- Hash Integrity Verification ---
        approved_diff = request.get("approved_diff_contents", "")
        expected_hash = request.get("approved_diff_hash", "")
        computed_hash = _sha256_of_string(approved_diff)

        if computed_hash != expected_hash:
            _write_receipt(
                receipt_path,
                status="failure",
                request=request,
                pre_promotion_head=pre_promotion_head,
                error_log=f"hash_mismatch: expected {expected_hash}, got {computed_hash}",
                post_check_status="not_ran",
                applied_artifact_hash=computed_hash
            )
            print(f"Pre-flight FAILED: hash_mismatch", file=sys.stderr)
            return 0

        # --- Run pre-flight checks ---
        errors = _preflight(request, repo)

        if errors:
            # Determine status: drift if HEAD/branch mismatch, otherwise failure
            is_drift = any("HEAD mismatch" in e or "Branch mismatch" in e for e in errors)
            status = "drift" if is_drift else "failure"
            _write_receipt(
                receipt_path,
                outcome_code="S2_APPLY_NOT_STARTED",
                request=request,
                apply_authorized=False,
                pre_promotion_head=pre_promotion_head,
                error_log="; ".join(errors),
                started_at=started_at
            )
            for err in errors:
                print(f"Pre-flight FAILED: {err}", file=sys.stderr)
            return 0

                # --- S2.2_APPLY_RECOVERY Phase ---
        approved_diff = request.get("approved_diff_contents", "")
        import tempfile, subprocess
        with tempfile.NamedTemporaryFile(mode="wb", prefix="promo_", suffix=".patch", delete=False) as tf:
            tf.write(approved_diff.encode("utf-8"))
            patch_path = tf.name

        try:
            apply_started = True
            apply_res = subprocess.run(
                ["git", "apply", "--index", patch_path],
                cwd=str(repo),
                capture_output=True,
                text=True
            )

            if apply_res.returncode == 0:
                apply_completed = True
                staged_hash = _get_staged_index_hash(repo)
                print(f"Apply OK. Staged Hash: {staged_hash}")
                
                # --- Verification Phase (Slice 2.3) ---
                # Detect affected files from index
                diff_res = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=str(repo), capture_output=True, text=True)
                affected = diff_res.stdout.splitlines()
                
                v_status, v_details = _run_safety_rails(repo, affected)
                
                if v_status == "pass":
                    # S2_VERIFIED_HUMAN_GATE_REQUIRED path
                    _write_receipt(
                        receipt_path,
                        outcome_code="S2_VERIFIED_HUMAN_GATE_REQUIRED",
                        request=request,
                        pre_promotion_head=pre_promotion_head,
                        apply_started=True,
                        apply_completed=True,
                        verification_status="pass",
                        verification_details=v_details,
                        staged_index_hash=staged_hash,
                        started_at=started_at
                    )
                    print("Verification PASSED. Staged for Human Review.")
                    return 0
                else:
                    # Post-check failure detected -> Trigger Rollback
                    print(f"Verification FAILED. Initiating Rollback.", file=sys.stderr)
                    rb_success = _rollback(repo, pre_promotion_head)
                    outcome = "S2_POSTCHECK_FAILED_ROLLBACK_CLEAN" if rb_success else "S2_POSTCHECK_FAILED_ROLLBACK_DIRTY"
                    _write_receipt(
                        receipt_path,
                        outcome_code=outcome,
                        request=request,
                        pre_promotion_head=pre_promotion_head,
                        error_log="Safety Rails failed after apply.",
                        apply_started=True,
                        apply_completed=True,
                        rollback_attempted=True,
                        rollback_result="success" if rb_success else "fail",
                        dirty_state_detected=not rb_success,
                        verification_status="fail",
                        verification_details=v_details,
                        staged_index_hash=staged_hash,
                        started_at=started_at
                    )
                    return 0
            else:
                raise RuntimeError(f"git apply failed: {apply_res.stderr.strip()}")

        except Exception as exc:
            rb_success = _rollback(repo, pre_promotion_head)
            outcome = "S2_APPLY_FAILED_ROLLBACK_CLEAN" if rb_success else "S2_APPLY_FAILED_ROLLBACK_DIRTY"
            _write_receipt(
                receipt_path,
                outcome_code=outcome,
                request=request,
                pre_promotion_head=pre_promotion_head,
                error_log=str(exc),
                apply_started=True,
                apply_completed=False,
                rollback_attempted=True,
                rollback_result="success" if rb_success else "fail",
                dirty_state_detected=not rb_success,
                started_at=started_at
            )
            print(f"Apply FAILED: {exc}. Rollback: {rb_success}", file=sys.stderr)
            return 0
        finally:
            import os
            if os.path.exists(patch_path):
                os.unlink(patch_path)


    except Exception as systemic_exc:
        # Systemic Integrity Escalation
        _write_receipt(
            receipt_path,
            outcome_code="S2_BLOCKED_AUDIT_REQUIRED",
            request=request,
            pre_promotion_head=pre_promotion_head,
            error_log=f"Systemic failure: {systemic_exc}",
            apply_started=apply_started,
            apply_completed=apply_completed,
            dirty_state_detected=apply_started, # Assume dirty if mutation might have started
            started_at=started_at
        )
        print(f"SYSTEMIC FAILURE: {systemic_exc}", file=sys.stderr)
        return 1
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    sys.exit(main())
