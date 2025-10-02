#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 2 ]; then echo "usage: $0 <target_bin> <crash.bin>"; exit 1; fi
python3 - <<'PY' "$@"
import os,sys,subprocess
from multiprocessing import shared_memory
MAP=1<<16
shm=shared_memory.SharedMemory(create=True,size=MAP)
env=os.environ.copy(); env['COV_SHM']=shm.name
p=subprocess.run([sys.argv[1], sys.argv[2]], env=env, capture_output=True)
print("RC:", p.returncode); print(p.stderr.decode('utf-8','ignore'))
PY
