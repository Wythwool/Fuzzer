#define _GNU_SOURCE
#include "cov.h"

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

static uint8_t *g_map;
static __thread uint16_t g_prev;

static void *map_shared_coverage(const char *name)
{
    char normalized[256];
    const char *shm_name = name;

    if (!name || !*name) {
        return NULL;
    }
    if (name[0] != '/') {
        snprintf(normalized, sizeof(normalized), "/%s", name);
        shm_name = normalized;
    }

    int fd = shm_open(shm_name, O_RDWR, 0600);
    if (fd < 0) {
        return NULL;
    }
    if (ftruncate(fd, COV_MAP_SIZE) < 0) {
        close(fd);
        return NULL;
    }

    void *mapped = mmap(NULL, COV_MAP_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    return mapped == MAP_FAILED ? NULL : mapped;
}

void cov_init_from_env(void)
{
    if (g_map) {
        return;
    }

    g_map = map_shared_coverage(getenv("COV_SHM"));
    if (!g_map) {
        g_map = mmap(NULL, COV_MAP_SIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (g_map != MAP_FAILED) {
            memset(g_map, 0, COV_MAP_SIZE);
        } else {
            g_map = NULL;
        }
    }
    g_prev = 0;
}

void cov_touch(uint16_t id)
{
    if (!g_map) {
        return;
    }

    uint16_t idx = (uint16_t)((g_prev ^ id) & (COV_MAP_SIZE - 1));
    g_map[idx]++;
    g_prev = (uint16_t)((id >> 1) | (id << 15));
}
