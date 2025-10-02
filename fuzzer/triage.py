#!/usr/bin/env python3
import os, sys, subprocess
from pathlib import Path
from multiprocessing import shared_memory
MAP_SIZE=1<<16
def run(bin_path, path, shm):
    shm.buf[:] = b'\x00'*MAP_SIZE
    env=os.environ.copy(); env['COV_SHM']=shm.name
    try:
        p=subprocess.run([bin_path, str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=0.3, env=env)
    except subprocess.TimeoutExpired:
        return False
    return (p.returncode<0) or (b'AddressSanitizer' in p.stderr) or (p.returncode in (139,134,11))
def minimize(bin_path, crash_path):
    shm=shared_memory.SharedMemory(create=True,size=MAP_SIZE)
    data=bytearray(Path(crash_path).read_bytes()); best=data[:]; changed=True
    while changed:
        changed=False; step=max(1,len(best)//16); i=0
        while i<len(best) and len(best)>4:
            cand=best[:i]+best[i+step:]; tmp=Path(crash_path).with_suffix('.tmp'); tmp.write_bytes(cand)
            if run(bin_path, tmp, shm): best=cand; changed=True; i=0; continue
            i+=step
        for i in range(len(best)):
            o=best[i]; 
            if o==0: continue
            best[i]=0; tmp=Path(crash_path).with_suffix('.tmp'); tmp.write_bytes(best)
            if run(bin_path, tmp, shm): changed=True; continue
            best[i]=o
    Path(crash_path).write_bytes(best); print(f"[+] minimized to {len(best)} bytes")
if __name__=='__main__':
    if len(sys.argv)<3: print("usage: triage.py <target_bin> <crash_file>"); sys.exit(1)
    minimize(sys.argv[1], sys.argv[2])
