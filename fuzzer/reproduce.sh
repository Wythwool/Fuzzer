#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -lt 2 ]; then
  echo "usage: $0 <target_bin> <crash.bin>" >&2
  exit 1
fi

python3 - <<'PY' "$@"
import os
import subprocess
import sys
from multiprocessing import shared_memory

MAP_SIZE = 1 << 16
shm = shared_memory.SharedMemory(create=True, size=MAP_SIZE)
env = os.environ.copy()
env["COV_SHM"] = shm.name
try:
    proc = subprocess.run([sys.argv[1], sys.argv[2]], env=env, capture_output=True, check=False)
    print("RC:", proc.returncode)
    if proc.stdout:
        print(proc.stdout.decode("utf-8", "ignore"), end="")
    if proc.stderr:
        print(proc.stderr.decode("utf-8", "ignore"), end="")
finally:
    shm.close()
    shm.unlink()
PY
