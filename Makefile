CC=gcc
CFLAGS=-O0 -g -fsanitize=address -Wall -Wextra -fno-omit-frame-pointer
TARGET=build/pngtoy
all: $(TARGET)
build: ; mkdir -p build findings corpus 2>/dev/null || true
$(TARGET): build cov/cov.c target/pngtoy.c cov/cov.h
	$(CC) $(CFLAGS) cov/cov.c target/pngtoy.c -o $(TARGET)
seed: build ; python3 target/gen_seed.py > corpus/seed.png
clean: ; rm -rf build findings fuzzer/__pycache__
.PHONY: all clean seed
