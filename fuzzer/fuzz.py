#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import random
import subprocess
import time
from dataclasses import dataclass
from multiprocessing import shared_memory
from pathlib import Path

MAP_SIZE = 1 << 16
DEFAULT_TIMEOUT = 0.25


@dataclass
class RunResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    elapsed_ms: float
    timed_out: bool = False

    @property
    def crashed(self) -> bool:
        if self.timed_out:
            return False
        return (
            self.returncode < 0
            or self.returncode in {11, 134, 139}
            or b"AddressSanitizer" in self.stderr
            or b"UndefinedBehaviorSanitizer" in self.stderr
        )


def mutate(data: bytes, rng: random.Random) -> bytes:
    if not data:
        return os.urandom(1)

    buf = bytearray(data)
    choice = rng.randint(0, 6)
    if choice == 0:
        for _ in range(rng.randint(1, 8)):
            pos = rng.randrange(len(buf))
            buf[pos] ^= 1 << rng.randrange(8)
    elif choice == 1:
        for _ in range(rng.randint(1, 8)):
            pos = rng.randrange(len(buf))
            buf[pos] = rng.choice([0, 1, 0x7F, 0x80, 0xFF])
    elif choice == 2:
        pos = rng.randrange(len(buf) + 1)
        buf[pos:pos] = rng.randbytes(rng.randint(1, 32))
    elif choice == 3 and len(buf) > 2:
        pos = rng.randrange(len(buf) - 1)
        size = rng.randint(1, min(32, len(buf) - pos))
        del buf[pos : pos + size]
    elif choice == 4:
        pos = rng.randrange(len(buf))
        width = rng.choice([0, 1, 2, 4])
        value = rng.choice([0, 1, 0xFFFF, 0xFFFFFFFF, rng.getrandbits(32)])
        raw = value.to_bytes(4, "big")
        buf[pos : pos + width] = raw[:width]
    elif choice == 5:
        src = rng.randrange(len(buf))
        size = rng.randint(1, min(32, len(buf) - src))
        dst = rng.randrange(len(buf) + 1)
        buf[dst:dst] = buf[src : src + size]
    else:
        for _ in range(rng.randint(1, 4)):
            pos = rng.randrange(len(buf))
            buf[pos] = (buf[pos] + rng.randint(-35, 35)) & 0xFF
    return bytes(buf)


def run_target(target: str, input_path: Path, shm: shared_memory.SharedMemory, timeout: float) -> RunResult:
    shm.buf[:] = b"\x00" * MAP_SIZE
    env = os.environ.copy()
    env["COV_SHM"] = shm.name
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            [target, str(input_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=timeout,
            check=False,
        )
        elapsed = (time.perf_counter() - start) * 1000
        return RunResult(proc.returncode, proc.stdout, proc.stderr, elapsed)
    except subprocess.TimeoutExpired as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return RunResult(124, exc.stdout or b"", exc.stderr or b"timeout", elapsed, True)


def merge_coverage(global_map: bytearray, shm: shared_memory.SharedMemory) -> int:
    gain = 0
    for idx, value in enumerate(shm.buf):
        if value and not global_map[idx]:
            global_map[idx] = 1
            gain += 1
    return gain


def load_corpus(corpus_dir: Path) -> list[Path]:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    return sorted(path for path in corpus_dir.iterdir() if path.is_file())


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def crash_key(data: bytes, result: RunResult) -> str:
    digest = hashlib.sha256()
    digest.update(data)
    digest.update(str(result.returncode).encode())
    digest.update(result.stderr[:2048])
    return digest.hexdigest()[:16]


def fuzz(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed if args.seed is not None else int.from_bytes(os.urandom(8), "big"))
    corpus = load_corpus(args.corpus)
    if not corpus:
        raise SystemExit("empty corpus")

    args.out.mkdir(parents=True, exist_ok=True)
    crashes = args.out / "crashes"
    queue = args.out / "queue"
    crashes.mkdir(exist_ok=True)
    queue.mkdir(exist_ok=True)

    global_map = bytearray(MAP_SIZE)
    seen_crashes: set[str] = set()
    stats = {
        "runs": 0,
        "crashes": 0,
        "unique_crashes": 0,
        "timeouts": 0,
        "new_paths": 0,
        "edges": 0,
        "corpus": len(corpus),
        "start_time": time.time(),
    }

    shm = shared_memory.SharedMemory(create=True, size=MAP_SIZE)
    current = args.out / ".cur_input"
    try:
        while args.max_runs == 0 or stats["runs"] < args.max_runs:
            parent = rng.choice(corpus)
            child = mutate(parent.read_bytes(), rng)
            current.write_bytes(child)
            result = run_target(args.target, current, shm, args.timeout)
            gain = merge_coverage(global_map, shm)

            stats["runs"] += 1
            stats["edges"] = sum(1 for byte in global_map if byte)
            if result.timed_out:
                stats["timeouts"] += 1

            if result.crashed:
                stats["crashes"] += 1
                key = crash_key(child, result)
                if key not in seen_crashes:
                    seen_crashes.add(key)
                    stats["unique_crashes"] += 1
                    crash_path = crashes / f"id_{stats['unique_crashes']:06d}_{key}.bin"
                    log_path = crash_path.with_suffix(".log")
                    crash_path.write_bytes(child)
                    log_path.write_bytes(result.stderr or result.stdout)
                    if not args.quiet:
                        print(f"[CRASH] {crash_path.name} rc={result.returncode} +edges={gain}")
            elif gain > 0:
                stats["new_paths"] += 1
                queue_path = queue / f"id_{stats['new_paths']:06d}.bin"
                queue_path.write_bytes(child)
                corpus.append(queue_path)
                stats["corpus"] = len(corpus)
                if not args.quiet:
                    print(f"[+] new path {queue_path.name} +edges={gain} corpus={len(corpus)}")

            if stats["runs"] % args.report_every == 0:
                save_json(args.out / "stats.json", stats)
                if not args.quiet:
                    print(
                        f"runs={stats['runs']} edges={stats['edges']} "
                        f"corpus={stats['corpus']} crashes={stats['unique_crashes']}"
                    )
        save_json(args.out / "stats.json", stats)
    finally:
        try:
            current.unlink(missing_ok=True)
        finally:
            shm.close()
            shm.unlink()

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Small coverage-guided fuzzer")
    parser.add_argument("target")
    parser.add_argument("corpus", type=Path)
    parser.add_argument("out", type=Path, nargs="?", default=Path("findings"))
    parser.add_argument("--max-runs", type=int, default=0, help="0 means run until interrupted")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--report-every", type=int, default=100)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> int:
    return fuzz(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
