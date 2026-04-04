import subprocess, os, sys, json, time
from pathlib import Path
from datetime import datetime

def _run_cmd(cmd_list, cwd_dir=None):
    process_res = subprocess.run(cmd_list, cwd=cwd_dir, capture_output=True, text=True, timeout=120)
    return int(process_res.returncode), str(process_res.stdout), str(process_res.stderr)

def run_health_checks(modified_files, venv_path, project_path):
    python_bin = os.path.join(venv_path, 'bin', 'python3')
    py_files = [f for f in modified_files if f.endswith('.py')]
    for f in py_files:
        abs_p = os.path.join(project_path, f) if not os.path.isabs(f) else f
        rc, _, se = _run_cmd([python_bin, '-m', 'py_compile', abs_p], cwd_dir=project_path)
        if rc != 0: return False, f'[LAYER 1 - Syntax] FAILED for {f}:\n{se}'
    for f in py_files:
        mod = f.replace('/', '.').replace('\\', '.').removesuffix('.py').lstrip('.')
        rc, _, se = _run_cmd([python_bin, '-c', f'import {mod}'], cwd_dir=project_path)
        if rc != 0: return False, f'[LAYER 2 - Import] FAILED for {mod}:\n{se}'
    rc, _, se = _run_cmd([python_bin, '-c', 'import main'], cwd_dir=project_path)
    if rc != 0: return False, f'[LAYER 3 - App Smoke] FAILED:\n{se}'
    return True, ''

def execute_task(req_path, proj_path):
    with open(req_path, 'r') as f: req_data = json.load(f)
    os.chdir(proj_path)
    
    t_start_iso = datetime.utcnow().isoformat() + "Z"
    t_start_unix = time.time()
    
    pre_h = subprocess.check_output("git rev-parse HEAD", shell=True, text=True).strip()
    base_b = subprocess.check_output("git rev-parse --abbrev-ref HEAD", shell=True, text=True).strip()
    
    b_name = f"harness-run-{{req_data['request_id']}}"
    rc_git, _, se_git = _run_cmd(['git', 'checkout', '-b', b_name])
    if rc_git != 0:
        # Error build logic
        sys.exit(1)

    p_path = f"/tmp/aider_p_{{req_data['request_id']}}.md"
    with open(p_path, 'w') as f:
        f.write(f"# TASK\n{{req_data['instruction']}}\n\n# FILES\n{{', '.join(req_data['target_files'])}}")
    
    f_str = " ".join(req_data['target_files'])
    a_cmd = f"bash run-aider.sh --message-file {{p_path}} --yes-always --no-gitignore {{f_str}}"
    a_rc, a_out, a_err = _run_cmd(['bash', '-c', a_cmd], cwd_dir=proj_path)
    
    try:
        mod_f = subprocess.check_output("git diff --name-only HEAD~1", shell=True, text=True).strip().split('\n')
        mod_f = [f for f in mod_f if f]
        g_diff = subprocess.check_output("git diff HEAD~1", shell=True, text=True)
    except:
        mod_f = []; g_diff = ""
    
    final_status = "failure"
    final_h = ""
    err_log = str(a_err)

    if a_rc == 0 and mod_f:
        ok, err = run_health_checks(mod_f, os.path.join(proj_path, '.venv'), proj_path)
        if ok:
            final_status = "success"
            final_h = subprocess.check_output("git rev-parse HEAD", shell=True, text=True).strip()
        else:
            err_log += f"\n{{err}}"

    # Cleanup
    _run_cmd(['git', 'checkout', base_b])
    if final_status != "success": _run_cmd(['git', 'branch', '-D', b_name])

    # JSON Build
    result = {
        "request_id": str(req_data['request_id']),
        "exec_request_hash": str(req_data.get('exec_request_hash', '')),
        "commit_hash": str(final_h),
        "approval_hash": str(req_data.get('approval_meta', {}).get('approval_hash', '')),
        "approved_at": str(req_data.get('approval_meta', {}).get('approved_at', '')),
        "approved_by_user": req_data.get('approval_meta', {}).get('approved_by_user'),
        "status": final_status,
        "execution_mode": "apply_in_temp_branch",
        "integrity_mode": "strict",
        "modified_files": mod_f,
        "git_diff": str(g_diff),
        "stdout": str(a_out),
        "stderr": str(err_log),
        "started_at": t_start_iso,
        "finished_at": datetime.utcnow().isoformat() + "Z",
        "duration_ms": int((time.time() - t_start_unix) * 1000),
        "base_branch": str(base_b),
        "final_branch": str(base_b),
        "cleanup_status": {"success": True},
        "tests": {"ran": False, "passed_count": 0, "failed_count": 0}
    }
    
    out_p = f"/tmp/exec_res_{{req_data['request_id']}}.json"
    with open(out_p, 'w') as f: json.dump(result, f, indent=2)
    print(out_p)

if __name__ == "__main__":
    execute_task(sys.argv[1], sys.argv[2])
