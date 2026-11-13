#!/usr/bin/env python3
"""Check that installed Lichii opens a main window, then terminate it."""
import os
from pathlib import Path
import subprocess
import tempfile
import time

with tempfile.TemporaryDirectory(prefix='lichii-smoke-') as folder:
    root = Path(folder)
    env = dict(os.environ, QT_QPA_PLATFORM='xcb', XDG_CONFIG_HOME=str(root/'config'), XDG_DATA_HOME=str(root/'data'), XDG_CACHE_HOME=str(root/'cache'))
    with (root/'startup.log').open('w+') as log:
        process = subprocess.Popen(['/usr/bin/lichii'], env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f'Lichii exited early: {process.returncode}')
                windows = subprocess.run(['xdotool','search','--onlyvisible','--pid',str(process.pid)],text=True,capture_output=True)
                for window in windows.stdout.splitlines():
                    title = subprocess.check_output(['xdotool','getwindowname',window],text=True).strip()
                    if 'lichii' in title.lower() and not any(word in title.lower() for word in ['stopped','error','failed']):
                        print('Lichii native GUI startup passed:',title)
                        raise SystemExit(0)
                time.sleep(0.25)
            raise RuntimeError('Lichii did not expose its main window within 20 seconds')
        except Exception:
            log.flush();log.seek(0)
            print(log.read()[-8000:])
            raise
        finally:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill();process.wait()
