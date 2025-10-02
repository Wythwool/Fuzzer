# covfuzz — tiny coverage-guided fuzzer (AFL-style)

Build:
```bash
make && make seed
```
Run:
```bash
python3 fuzzer/fuzz.py build/pngtoy corpus findings
```
Reproduce crash:
```bash
bash fuzzer/reproduce.sh build/pngtoy findings/crashes/id_*.bin
```
