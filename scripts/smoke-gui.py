#!/usr/bin/env python3
"""Check that a packaged GUI opens a main window, then terminate it."""
import os
import sys
from pathlib import Path
import subprocess
import tempfile
import time

program, expected_title = sys.argv[1:3]
with tempfile.TemporaryDirectory(prefix='desktop-smoke-') as folder:
    root = Path(folder)
    runtime = root / 'runtime'
    runtime.mkdir(mode=0o700)
    env = dict(os.environ, GDK_BACKEND='x11', GSK_RENDERER='cairo', GTK_A11Y='none', XDG_RUNTIME_DIR=str(runtime), QT_QPA_PLATFORM='xcb', XDG_CONFIG_HOME=str(root/'config'), XDG_DATA_HOME=str(root/'data'), XDG_CACHE_HOME=str(root/'cache'))
    with (root/'startup.log').open('w+') as log:
        process = subprocess.Popen([program], env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f'{expected_title} exited early: {process.returncode}')
                windows = subprocess.run(['xdotool','search','--onlyvisible','--pid',str(process.pid)],text=True,capture_output=True)
                for window in windows.stdout.splitlines():
                    title = subprocess.check_output(['xdotool','getwindowname',window],text=True).strip()
                    if expected_title.lower() in title.lower() and not any(word in title.lower() for word in ['stopped','error','failed']):
                        print(expected_title + ' native GUI startup passed:',title)
                        raise SystemExit(0)
                time.sleep(0.25)
            raise RuntimeError(expected_title + ' did not expose its main window within 20 seconds')
        except Exception:
            log.flush();log.seek(0)
            print(log.read()[-8000:])
            raise
        finally:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill();process.wait()
