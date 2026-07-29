"""Bounded local security checks that are safe to run in CI."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    checks=[]
    secret=subprocess.run([sys.executable,str(ROOT/'scripts/check_secrets.py')],cwd=ROOT,capture_output=True,text=True)
    checks.append({"id":"secret_scan","passed":secret.returncode==0})
    checks.extend([
        {"id":"production_env_ignored","passed":is_ignored('.env.production')},
        {"id":"secrets_dir_ignored","passed":is_ignored('secrets/database_url.txt')},
        {"id":"max_request_configured","passed":'MAX_CONTENT_LENGTH' in (ROOT/'platform_api/app.py').read_text()},
        {"id":"csrf_configured","passed":'compare_digest' in (ROOT/'platform_api/app.py').read_text()},
        {"id":"session_cookie_httponly","passed":'SESSION_COOKIE_HTTPONLY=True' in (ROOT/'platform_api/app.py').read_text()},
    ])
    print(json.dumps({"status":"passed" if all(x['passed'] for x in checks) else "failed","checks":checks}))
    return 0 if all(x["passed"] for x in checks) else 2
def is_ignored(path):
    return subprocess.run(["git","check-ignore","-q",path],cwd=ROOT).returncode==0
if __name__=="__main__": raise SystemExit(main())
