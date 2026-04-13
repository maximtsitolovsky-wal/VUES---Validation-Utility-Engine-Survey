"""startup_check.py - Verify main.py starts and loads config without crashing."""
import subprocess, sys, time

print('Starting main.py for 5 seconds to verify clean startup...')
print()

proc = subprocess.Popen(
    [sys.executable, '-u', 'main.py'],
    cwd=r'C:\SiteOwlQA_App',
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

lines = []
deadline = time.time() + 6
while time.time() < deadline:
    try:
        line = proc.stdout.readline()
        if line:
            print(' ', line.rstrip())
            lines.append(line)
    except Exception:
        break

proc.terminate()
proc.wait(timeout=5)

print()
ok = any(
    'Polling Airtable' in l or
    'MetricsRefreshWorker started' in l or
    'Version : 1.2.0' in l or
    'Started 1 worker thread' in l
    for l in lines
)
if ok:
    print('STARTUP CHECK PASSED - main.py starts cleanly.')
else:
    print('STARTUP CHECK: could not confirm clean startup - check output above.')
