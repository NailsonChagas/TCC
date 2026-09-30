def _c_float(value):
    return f"{value}" + ("" if "." in f"{value}" else ".0")

def generate_c_code(coeffs, n_val, d_val, filename="buck_model.c"):
    n_points = coeffs['n_points']
    closed_steps = int(n_val * d_val)

    c_code = f"""#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

typedef struct {{
    float iL;
    float vC;
}} BuckState;

static const float Ad_00 = {_c_float(coeffs['Ad_00'])}f;
static const float Ad_01 = {_c_float(coeffs['Ad_01'])}f;
static const float Ad_10 = {_c_float(coeffs['Ad_10'])}f;
static const float Ad_11 = {_c_float(coeffs['Ad_11'])}f;

static const float Bd1_00_Vs = {_c_float(coeffs['Bd1_00_Vs'])}f;
static const float Bd1_10_Vs = {_c_float(coeffs['Bd1_10_Vs'])}f;

static const float Bd2_00_Vs = {_c_float(coeffs['Bd2_00_Vs'])}f;
static const float Bd2_10_Vs = {_c_float(coeffs['Bd2_10_Vs'])}f;

__attribute__((noinline))
void buck_step(BuckState *x, bool switch_closed) {{
    float iL = x->iL;
    float vC = x->vC;

    if (switch_closed) {{
        x->iL = Ad_00 * iL + Ad_01 * vC + Bd1_00_Vs;
        x->vC = Ad_10 * iL + Ad_11 * vC + Bd1_10_Vs;
    }} else {{
        x->iL = Ad_00 * iL + Ad_01 * vC + Bd2_00_Vs;
        x->vC = Ad_10 * iL + Ad_11 * vC + Bd2_10_Vs;
    }}
}}

int main(void) {{
    BuckState state = {{ .iL = 0.0f, .vC = 0.0f }};
    const uint32_t N_steps = {n_points};

    for (uint32_t k = 0; k < N_steps - 1; k++) {{
        bool switch_closed = (k % {n_val}) < {closed_steps};
        buck_step(&state, switch_closed);
    }}

    printf("iL = %.6f\\n", state.iL);
    printf("vC = %.6f\\n", state.vC);
    return 0;
}}
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(c_code)
    
    print(f"[C Generator] Arquivo gerado com sucesso: {filename}")