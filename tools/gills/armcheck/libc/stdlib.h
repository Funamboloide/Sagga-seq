#pragma once
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
void *malloc(size_t); void free(void *); int abs(int); long labs(long); int atoi(const char *);
int rand(void); void srand(unsigned); void abort(void); void exit(int);
#ifdef __cplusplus
}
#endif
