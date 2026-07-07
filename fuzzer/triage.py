#!/usr/bin/env python3
import argparse
import os
import subprocess
from multiprocessing import shared_memory
from pathlib import Path

MAP_SIZE = 1 << 16


def crashes(target: str, path: Path, shm: shared_memory.SharedMemory, timeout: float) -> bool:
    shm.buf[:] = b"\x00" * MAP_SIZE
    env = os.environ.copy()
    env["COV_SHM"] = shm.name
    try:
        proc = subprocess.run(
            [target, str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False
    return (
        proc.returncode < 0
        or proc.returncode in {11, 134, 139}
        or b"AddressSanitizer" in proc.stderr
        or b"UndefinedBehaviorSanitizer" in proc.stderr
    )


def minimize(target: str, crash_path: Path, out_path: Path, timeout: float) -> int:
    data = bytearray(crash_path.read_bytes())
    best = data[:]
    tmp = out_path.with_suffix(".tmp")
    shm = shared_memory.SharedMemory(create=True, size=MAP_SIZE)
    try:
        if not crashes(target, crash_path, shm, timeout):
            raise SystemExit(f"{crash_path} does not reproduce")

        changed = True
        while changed:
            changed = False
            step = max(1, len(best) // 16)
            pos = 0
            while pos < len(best) and len(best) > 4:
                candidate = best[:pos] + best[pos + step :]
                tmp.write_bytes(candidate)
                if crashes(target, tmp, shm, timeout):
                    best = candidate
                    changed = True
                    pos = 0
                    continue
                pos += step

            for pos in range(len(best)):
                old = best[pos]
                if old == 0:
                    continue
                best[pos] = 0
                tmp.write_bytes(best)
                if crashes(target, tmp, shm, timeout):
                    changed = True
                    continue
                best[pos] = old

        out_path.write_bytes(best)
        print(f"minimized {len(data)} -> {len(best)} bytes: {out_path}")
        return 0
    finally:
        tmp.unlink(missing_ok=True)
        shm.close()
        shm.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimize a reproducible crash input")
    parser.add_argument("target")
    parser.add_argument("crash_file", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--timeout", type=float, default=0.5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = args.out or args.crash_file.with_suffix(".min.bin")
    return minimize(args.target, args.crash_file, out, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
