#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float iL;
    float vC;
} BuckState;

static const float Ad_00 = 0.9999265803813119f;
static const float Ad_01 = -0.00013156940067175223f;
static const float Ad_10 = 1.0964116722646022f;
static const float Ad_11 = 0.9736337345236475f;

static const float Bd1_00_Vs = 0.00666650314952061f;
static const float Bd1_10_Vs = 0.0036709809344059874f;

static const float Bd2_00_Vs = 0.0f;
static const float Bd2_10_Vs = 0.0f;

__attribute__((noinline))
void buck_step(BuckState *x, bool switch_closed) {
    volatile float iL = x->iL;
    volatile float vC = x->vC;

    if (switch_closed) {
        x->iL = Ad_00 * iL + Ad_01 * vC + Bd1_00_Vs;
        x->vC = Ad_10 * iL + Ad_11 * vC + Bd1_10_Vs;
    } else {
        x->iL = Ad_00 * iL + Ad_01 * vC + Bd2_00_Vs;
        x->vC = Ad_10 * iL + Ad_11 * vC + Bd2_10_Vs;
    }
}

int main(void) {
    BuckState state = { .iL = 0.0f, .vC = 0.0f };
    const uint32_t N_steps = 29999;

    for (uint32_t k = 0; k < N_steps - 1; k++) {
        bool switch_closed = (k % 100) < 50;
        buck_step(&state, switch_closed);
    }

    printf("iL = %.6f\n", state.iL);
    printf("vC = %.6f\n", state.vC);
    return 0;
}
