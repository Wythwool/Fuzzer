import random
import tempfile
import unittest
from multiprocessing import shared_memory
from pathlib import Path

from fuzzer.fuzz import MAP_SIZE, merge_coverage, mutate


class FuzzerTests(unittest.TestCase):
    def test_mutation_is_deterministic_with_seed(self):
        data = b"\x89PNG\r\n\x1a\n" + bytes(range(32))
        first = mutate(data, random.Random(1234))
        second = mutate(data, random.Random(1234))
        self.assertEqual(first, second)
        self.assertNotEqual(first, data)

    def test_coverage_merge_counts_new_edges_once(self):
        shm = shared_memory.SharedMemory(create=True, size=MAP_SIZE)
        try:
            global_map = bytearray(MAP_SIZE)
            shm.buf[10] = 1
            shm.buf[20] = 2
            self.assertEqual(merge_coverage(global_map, shm), 2)
            self.assertEqual(merge_coverage(global_map, shm), 0)
        finally:
            shm.close()
            shm.unlink()

    def test_temp_path_usage_is_plain_filesystem(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.bin"
            path.write_bytes(b"abc")
            self.assertEqual(path.read_bytes(), b"abc")


if __name__ == "__main__":
    unittest.main()
