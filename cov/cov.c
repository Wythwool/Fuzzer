#include "cov.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

static uint8_t *g_map;
static __thread uint16_t g_prev;

static void* map_shm(const char* name){
    if(!name) return NULL;
    char buf[256];
    const char* nm = name;
    if(name[0] != '/'){ snprintf(buf, sizeof(buf), "/%s", name); nm = buf; }
    int fd = shm_open(nm, O_RDWR, 0600);
    if(fd < 0) return NULL;
    if(ftruncate(fd, COV_MAP_SIZE) < 0){ close(fd); return NULL; }
    void* p = mmap(NULL, COV_MAP_SIZE, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    return (p==MAP_FAILED)? NULL : p;
}
void cov_init_from_env(void){
    if(g_map) return;
    const char* nm = getenv("COV_SHM");
    g_map = (uint8_t*)map_shm(nm);
    if(!g_map){
        g_map = (uint8_t*)mmap(NULL, COV_MAP_SIZE, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANON, -1, 0);
        if(g_map && g_map!=(void*)-1) memset(g_map, 0, COV_MAP_SIZE);
    }
    g_prev = 0;
}
void cov_touch(uint16_t id){
    if(!g_map) return;
    uint16_t idx = (g_prev ^ id) & (COV_MAP_SIZE-1);
    g_map[idx]++;
    g_prev = (id >> 1) | (id << 15);
}
