#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../cov/cov.h"

static uint32_t be32(const unsigned char *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

static unsigned char *read_file(const char *path, size_t *len)
{
    FILE *file = fopen(path, "rb");
    if (!file) {
        perror("open");
        return NULL;
    }

    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return NULL;
    }
    long size = ftell(file);
    if (size < 0) {
        fclose(file);
        return NULL;
    }
    rewind(file);

    unsigned char *buf = malloc((size_t)size);
    if (!buf && size > 0) {
        fclose(file);
        return NULL;
    }
    if (size > 0 && fread(buf, 1, (size_t)size, file) != (size_t)size) {
        free(buf);
        fclose(file);
        return NULL;
    }

    fclose(file);
    *len = (size_t)size;
    return buf;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <file>\n", argv[0]);
        return 2;
    }

    size_t size = 0;
    unsigned char *buf = read_file(argv[1], &size);
    if (!buf) {
        return 2;
    }
    if (size < 8 || memcmp(buf, "\x89PNG\r\n\x1a\n", 8) != 0) {
        free(buf);
        return 0;
    }
    COV_POINT();

    if (size < 33) {
        free(buf);
        return 0;
    }

    uint32_t ihdr_len = be32(buf + 8);
    COV_POINT();
    if (memcmp(buf + 12, "IHDR", 4) != 0 || ihdr_len < 13) {
        free(buf);
        return 0;
    }

    uint32_t width = be32(buf + 16);
    uint32_t height = be32(buf + 20);
    COV_POINT();
    if (width == 0 || height == 0 || width > 20000 || height > 20000) {
        free(buf);
        return 0;
    }

    size_t pixels = (size_t)width * (size_t)height;
    size_t cap = (pixels > 0 && pixels < 65536) ? pixels : 65536;
    unsigned char *image = malloc(cap);
    if (!image) {
        free(buf);
        return 2;
    }

    size_t off = 0;
    size_t pos = 8;
    while (pos + 8 <= size) {
        uint32_t chunk_len = be32(buf + pos);
        pos += 4;
        if (pos + 4 > size) {
            break;
        }

        char chunk_type[5] = {0};
        memcpy(chunk_type, buf + pos, 4);
        pos += 4;
        COV_POINT();

        if (pos + chunk_len + 4 > size) {
            break;
        }
        if (memcmp(chunk_type, "IDAT", 4) == 0) {
            COV_POINT();
            memcpy(image + off, buf + pos, chunk_len);
            off += chunk_len;
        } else if (memcmp(chunk_type, "IEND", 4) == 0) {
            COV_POINT();
            break;
        } else {
            COV_POINT();
        }
        pos += chunk_len + 4;
    }

    if (off > cap) {
        fprintf(stderr, "[BUG] overflow off=%zu cap=%zu\n", off, cap);
    }

    free(image);
    free(buf);
    return 0;
}
