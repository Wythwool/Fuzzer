#!/usr/bin/env python3
import os, sys, time, random, subprocess
from pathlib import Path
from multiprocessing import shared_memory
MAP_SIZE=1<<16; TIMEOUT=0.25
def mutate(d: bytes)->bytes:
    b=bytearray(d)
    c=random.randint(0,4)
    if c==0 and len(b): 
        for _ in range(random.randint(1,8)):
            i=random.randrange(len(b)); b[i]^=1<<random.randrange(8)
    elif c==1 and len(b):
        for _ in range(random.randint(1,8)):
            i=random.randrange(len(b)); b[i]=random.choice([0,0xff,0x7f,0x80])
    elif c==2:
        pos=random.randrange(len(b)+1); chunk=os.urandom(random.randint(1,16)); b[pos:pos]=chunk
    elif c==3 and len(b)>2:
        pos=random.randrange(len(b)-1); ln=random.randint(1,min(16,len(b)-pos)); del b[pos:pos+ln]
    else:
        for _ in range(random.randint(1,4)):
            i=random.randrange(len(b)); b[i]=(b[i]+random.randint(-35,35))&0xff
    return bytes(b)
def run(bin_path, inp, shm):
    shm.buf[:] = b'\x00'*MAP_SIZE
    env=os.environ.copy(); env['COV_SHM']=shm.name
    try:
        p=subprocess.run([bin_path, str(inp)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=TIMEOUT)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 999, b'', b'timeout'
def cov_gain(global_map, shm):
    g=0; buf=shm.buf
    for i in range(MAP_SIZE):
        if buf[i] and not global_map[i]: global_map[i]=1; g+=1
    return g
def main():
    if len(sys.argv)<3: print("usage: fuzz.py <target_bin> <corpus_dir> [out_dir]"); sys.exit(1)
    bin_path=sys.argv[1]; corp=Path(sys.argv[2]); corp.mkdir(exist_ok=True); out=Path(sys.argv[3] if len(sys.argv)>3 else "findings"); out.mkdir(exist_ok=True)
    crashes=(out/'crashes'); crashes.mkdir(exist_ok=True); queue=(out/'queue'); queue.mkdir(exist_ok=True)
    q=[p for p in corp.iterdir() if p.is_file()]
    if not q: print("[-] empty corpus"); sys.exit(1)
    shm=shared_memory.SharedMemory(create=True,size=MAP_SIZE); global_map=bytearray(MAP_SIZE); it=0
    while True:
        it+=1
        parent=random.choice(q); data=parent.read_bytes(); child=mutate(data)
        tmp=out/'cur.bin'; tmp.write_bytes(child)
        rc, outb, errb=run(bin_path, tmp, shm)
        gain=cov_gain(global_map, shm)
        if rc<0 or (b'AddressSanitizer' in errb) or rc in (139,134,11):
            ts=int(time.time()*1000); (crashes/f"id_{ts}.bin").write_bytes(child); (crashes/f"id_{ts}.log").write_bytes(errb or outb)
            print(f"[CRASH] id_{ts}.bin rc={rc} +edges={gain}")
        elif gain>0:
            nid=len(list(queue.iterdir())); pth=queue/f"id_{nid:06d}.bin"; pth.write_bytes(child); q.append(pth)
            print(f"[+] new path {pth.name} +edges={gain} corpus={len(q)}")
        if it%100==0: print(f"iter={it} total_edges={sum(global_map)} corpus={len(q)}")
if __name__=='__main__':
    random.seed(os.urandom(8)); main()
