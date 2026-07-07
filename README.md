# covfuzz

`covfuzz` is a compact coverage-guided fuzzing lab. It includes a tiny shared-memory edge coverage runtime, a Python mutation harness, crash reproduction, crash minimization, and an intentionally vulnerable PNG-like parser target.

The project is meant for learning, CI experiments, and small parser harnesses.

## Build

```bash
make
make seed
```

The target is built with AddressSanitizer and UndefinedBehaviorSanitizer so memory errors produce useful crash logs.

## Run

```bash
python3 fuzzer/fuzz.py build/pngtoy corpus findings --max-runs 10000 --seed 1337
```

Useful options:

- `--max-runs 0`: run until interrupted
- `--timeout 0.25`: per-input timeout in seconds
- `--seed N`: deterministic mutation stream
- `--report-every N`: write `findings/stats.json` every N runs
- `--quiet`: keep CI output short

Findings layout:

```text
findings/
  crashes/     unique crash inputs and logs
  queue/       inputs that discovered new coverage
  stats.json   run counters and corpus size
```

## Reproduce And Minimize

```bash
bash fuzzer/reproduce.sh build/pngtoy findings/crashes/id_000001_deadbeef.bin
python3 fuzzer/triage.py build/pngtoy findings/crashes/id_000001_deadbeef.bin
```

The minimizer writes `*.min.bin` and leaves the original crash input intact.

## Tests

```bash
make test
```

`make test` builds the toy target, regenerates the seed corpus, runs Python unit tests, and performs a short deterministic fuzzing pass.
