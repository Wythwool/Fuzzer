#pragma once
#include <stdint.h>
#define COV_MAP_SIZE (1<<16)
void cov_init_from_env(void);
void cov_touch(uint16_t id);
#ifdef __GNUC__
__attribute__((constructor)) static void __cov_ctor(void){ cov_init_from_env(); }
#endif
static inline uint16_t cov_id_hash(unsigned x){ return (uint32_t)(x * 2654435761u) & (COV_MAP_SIZE-1); }
#define COV_POINT() cov_touch(cov_id_hash(__LINE__))
