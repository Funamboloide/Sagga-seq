#pragma once
#ifdef __cplusplus
extern "C" {
#endif
float sinf(float); float cosf(float); float expf(float); float logf(float); float powf(float, float);
float sqrtf(float); float tanhf(float); float fabsf(float); float floorf(float); float tanf(float); float log10f(float); float exp2f(float); float log2f(float); float atanf(float); float roundf(float); float fmodf(float,float); float ceilf(float);
double sin(double); double cos(double); double exp(double); double log(double); double pow(double, double);
double sqrt(double); double fabs(double); double floor(double); double tan(double); double log10(double); double ceil(double); double fmod(double,double); double atan(double); double tanh(double); double round(double); double exp2(double);
#define M_PI 3.14159265358979323846
#define HUGE_VALF __builtin_huge_valf()
#ifdef __cplusplus
}
#endif
