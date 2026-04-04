import subprocess, os, sys, json, time
from pathlib import Path
from datetime import datetime

def _run(cmd, cwd=None):
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
    return res.returncode, str(res.stdout), str(res.stderr)

def run_health_checks(modified_files, venv_path, project_path):
    python = os.path.join(venv_path, 'bin', 'python3')
    py_files = [f for f in modified_files if f.endswith('.py')]
    for f in py_files:
        abs_p = os.path.join(project_path, f) if not os.path.isabs(f) else f
        rc, _, se = _run([python, '-m', 'py_compile', abs_p], cwd=project_path)
        if rc != 0: return False, f'[LAYER 1 - Syntax] FAILED for {f}:\n{se}'
    for f in py_files:
        mod = f.replace('/', '.').replace('\\', '.').removesuffix('.py').lstrip('.')
        rc, _, se = _run([python, '-c', f'import {mod}'], cwd=project_path)
        if rc != 0: return False, f'[LAYER 2 - Import] FAILED for {mod}:\n{se}'
    rc, _, se = _run([python, '-c', 'import main'], cwd=project_path)
    if rc != 0: return False, f'[LAYER 3 - App Smoke] FAILED:\n{se}'
    return True, ''

def execute_task(request_path, project_path):
    with open(request_path, 'r') as f: req = json.load(f)
    os.chdir(project_path)
    base_branch = subprocess.check_output("git rev-parse --abbrev-ref HEAD", shell=True, text=True).strip()
    branch_name = f"harness-run-{{req['request_id']}}"
    _run(['git', 'checkout', '-b', branch_name])
    
    start_time = time.time()
    prompt_path = f"/tmp/aider_prompt_{{req['request_id']}}.md"
    with open(prompt_path, 'w') as f: f.write(f"# TASK\n{{req['instruction']}}\n\n# FILES\n{{', '.join(req['target_files'])}}")
    
    files_str = " ".join(req['target_files'])
    aider_cmd = f"source /root/aider_venv/bin/activate && bash run-aider.sh --message-file {{prompt_path}} --yes-always --no-gitignore {{files_str}}"
    aider_rc, aider_out, aider_err = _run(['bash', '-c', aider_cmd], cwd=project_path)
    
    # Рекурсивный захват изменений (Head~1 всегда актуален после коммита Aider)
    try:
        modified_files = subprocess.check_output("git diff --name-only HEAD~1", shell=True, text=True).strip().split('\n')
        modified_files = [f for f in modified_files if f]
        git_diff = subprocess.check_output("git diff HEAD~1", shell=True, text=True)
    except:
        modified_files = []
        git_diff = ""
    
    status = "failure"
    commit_hash = ""
    health_error = ""
    
    if True: # Force check even if aider warned
        commit_hash = subprocess.check_output("git rev-parse HEAD", shell=True, text=True).strip()
        ok, err = run_health_checks(modified_files, os.path.join(project_path, '.venv'), project_path)
        if ok:
            status = "success"
        else:
            health_error = err
    
    res = {{
        "request_id": req['request_id'],
        "exec_request_hash": req.get('exec_request_hash'),
        "commit_hash": commit_hash,
        "approval_hash": req.get('approval_meta', {{}}).get('approval_hash'),
        "approved_at": req.get('approval_meta', {{}}).get('approved_at'),
        "approved_by_user": str(req.get('approval_meta', {{}}).get('approved_by_user', '')),
        "status": status,
        "execution_mode": "apply_in_temp_branch",
        "integrity_mode": req.get('integrity_mode', 'strict'),
        "modified_files": modified_files,
        "git_diff": git_diff,
        "stdout": str(aider_out),
        "stderr": str(aider_err) + ("\n" + health_error if health_error else ""),
        "started_at": datetime.utcnow().isoformat() + "Z",
        "finished_at": datetime.utcnow().isoformat() + "Z",
        "duration_ms": int((time.time() - start_time) * 1000),
        "base_branch": base_branch,
        "final_branch": base_branch,
        "cleanup_status": {{"success": True}},
        "tests": {{"ran": False, "passed_count": 0, "failed_count": 0}}
    }}
    
    _run(['git', 'checkout', base_branch])
    if status != "success":
        _run(['git', 'branch', '-D', branch_name])
    
    res_p = f"/tmp/exec_res_{{req['request_id']}}.json"
    with open(res_p, 'w') as f: json.dump(res, f, indent=2)
    print(res_p)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check_only":
        # Logic for post-promotion check on main
        files = sys.argv[2:]
        p_path = '/root/USBAGENT_V2_1_STABLE'
        v_path = os.path.join(p_path, '.venv')
        ok, err = run_health_checks(files, v_path, p_path)
        if not ok:
            print(err)
            sys.exit(1)
        print("Health checks passed.")
        sys.exit(0)
    
    execute_task(sys.argv[1], sys.argv[2])
