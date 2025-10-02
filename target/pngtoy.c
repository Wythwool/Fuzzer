#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "../cov/cov.h"
static uint32_t be32(const unsigned char* p){ return (p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3]; }
int main(int argc, char** argv){
    if(argc<2){ fprintf(stderr,"usage: %s <file>\n", argv[0]); return 2; }
    FILE* f=fopen(argv[1],"rb"); if(!f){ perror("open"); return 2; }
    fseek(f,0,SEEK_END); long sz=ftell(f); fseek(f,0,SEEK_SET);
    if(sz<8){ fclose(f); return 0; }
    unsigned char* b=malloc(sz); if(!b){ fclose(f); return 2; }
    fread(b,1,sz,f); fclose(f);
    if(sz<8 || memcmp(b,"\x89PNG\r\n\x1a\n",8)!=0){ free(b); return 0; }
    COV_POINT();
    if(sz<33){ free(b); return 0; }
    uint32_t ih_len=be32(b+8); COV_POINT();
    if(memcmp(b+12,"IHDR",4)!=0){ free(b); return 0; }
    if(ih_len<13){ free(b); return 0; }
    uint32_t W=be32(b+16), H=be32(b+20); COV_POINT();
    if(W==0 || H==0 || W>20000 || H>20000){ free(b); return 0; }
    size_t maxpix=(size_t)W*(size_t)H;
    size_t cap=(maxpix>0 && maxpix<65536)?maxpix:65536;
    unsigned char* img=malloc(cap);
    size_t off=0;
    size_t p=8;
    while(p+8<=(size_t)sz){
        uint32_t clen=be32(b+p); p+=4;
        if(p+4>(size_t)sz) break;
        char ctype[5]={0}; memcpy(ctype,b+p,4); p+=4; COV_POINT();
        if(p+clen+4>(size_t)sz) break;
        if(!memcmp(ctype,"IDAT",4)){
            COV_POINT();
            memcpy(img+off,b+p,clen); // BUG: no bounds check
            off+=clen;
        }else if(!memcmp(ctype,"IEND",4)){ COV_POINT(); break; }
        else{ COV_POINT(); }
        p+=clen+4;
    }
    if(off>cap){ fprintf(stderr,"[BUG] overflow off=%zu cap=%zu\n",off,cap); }
    free(img); free(b);
    return 0;
}
