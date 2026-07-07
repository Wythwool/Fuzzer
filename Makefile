CC ?= gcc
PYTHON ?= python3
CFLAGS ?= -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer
CFLAGS += -std=c11 -Wall -Wextra -Werror
TARGET := build/pngtoy

all: $(TARGET)

build:
	mkdir -p build findings corpus

$(TARGET): build cov/cov.c target/pngtoy.c cov/cov.h
	$(CC) $(CFLAGS) cov/cov.c target/pngtoy.c -o $(TARGET)

seed: build
	$(PYTHON) target/gen_seed.py > corpus/seed.png

test: all seed
	$(PYTHON) -m unittest discover -s tests
	$(PYTHON) fuzzer/fuzz.py $(TARGET) corpus findings --max-runs 25 --seed 7 --timeout 0.5 --quiet

clean:
	rm -rf build findings fuzzer/__pycache__ tests/__pycache__

.PHONY: all build clean seed test
