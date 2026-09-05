import numpy as np
import pandas as pd
from scipy.linalg import expm
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, MaxNLocator

FONT_TITLE = 16    
FONT_LABEL = 13    
FONT_TICKS = 12    
FONT_LEGEND = 13 
DPI = 500          

# --- IMPORTAÇÃO DOS DADOS DO QSPICE ---
# Certifique-se de que o arquivo buck_filtro_controle.csv está na mesma pasta
df = pd.read_csv("buck_filtro_controle.csv")
t_qspice = df['Time'].values
vC_qspice_data = df['V(buck)'].values
iL_qspice_data = df['I(L1)'].values
D_qspice_data = df['V(duty_cycle)'].values

# Interpoladores para parear o tempo do Python com o tempo do QSPICE
interp_vC = interp1d(t_qspice, vC_qspice_data, fill_value="extrapolate")
interp_iL = interp1d(t_qspice, iL_qspice_data, fill_value="extrapolate")
interp_D = interp1d(t_qspice, D_qspice_data, kind='previous', fill_value="extrapolate")

# --- CONFIGURAÇÕES DA SIMULAÇÃO ---
F_MULTIPLIERS = np.unique(np.concatenate([
    np.arange(1, 11, 1),
    np.arange(10, 101, 10),
    np.arange(100, 1001, 100),
    np.arange(1000, 10001, 1000)
]))
ticks_to_show = [1, 10, 100, 1000, 10000]

methods = ['zoh'] # Mantido apenas ZOH

T_END = 0.006
Fs = 50e3
L = 1.5e-3
R = 41.7
C = 0.18e-6
V_ref = 25

# Dicionário para armazenar o histórico de erros
errors = {
    'vC': {m: [] for m in methods},
    'iL': {m: [] for m in methods},
    'D':  {m: [] for m in methods}
}

# Função de erro relativo percentual (ignora instantes onde a ref é muito próxima de 0)
def calc_mape(sim, ref, threshold):
    mask = np.abs(ref) > threshold
    if np.sum(mask) == 0: return 0.0
    return np.mean(np.abs(sim[mask] - ref[mask]) / np.abs(ref[mask])) * 100

def filter_step(x_k, x_k1, x_k2, y_k1, y_k2):
    return (1.09727 * y_k1) - (0.33759 * y_k2) + \
           (0.06008 * x_k) + (0.12016 * x_k1) + (0.06008 * x_k2)

def controller_step(e_k, e_k1, u_k1):
    return u_k1 + (0.001906 * e_k) + (0.00049680633 * e_k1)

# --- VARREDURA DE MULTIPLICADORES ---
for f_mult in F_MULTIPLIERS:
    print(f_mult)
    Tsim = 1 / (f_mult * Fs)
    n_points = int(T_END / Tsim)
    t_sim = np.arange(n_points) * Tsim 

    Vs_array = np.full(n_points, 50.0)
    idx_step = int((T_END/2) / Tsim)
    Vs_array[idx_step:] = 60.0

    # 1. ZOH
    A = np.array([[0, -1/L], [1/C, -1/(R*C)]])
    B1 = np.array([1/L, 0])
    Ad = expm(A * Tsim)
    A_inv = np.linalg.inv(A)
    Bd1 = A_inv @ (Ad - np.eye(2)) @ B1  

    # Obter o sinal de referência no mesmo domínio de tempo (t_sim)
    vC_qspice = interp_vC(t_sim)
    iL_qspice = interp_iL(t_sim)
    D_qspice = interp_D(t_sim)

    for method in methods:
        iL = np.zeros(n_points)
        vC = np.zeros(n_points)
        D_array = np.zeros(n_points)

        e_k, e_k1 = 0.0, 0.0
        u_k1 = 0.0 
        x_k, x_k1, x_k2 = 0.0, 0.0, 0.0
        y_k1, y_k2 = 0.0, 0.0
        D_val = u_k1

        # simulação
        for k in range(n_points - 1):
            is_switch_closed = (k % f_mult) < (D_val * f_mult)
            
            if method == 'zoh':
                if is_switch_closed:
                    iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k] + Bd1[0]*Vs_array[k]
                    vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k] + Bd1[1]*Vs_array[k]
                else:
                    iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k]
                    vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k]

            # Atualização do Filtro e Controle
            if (k + 1) % f_mult == 0:
                x_k2 = x_k1
                x_k1 = x_k
                x_k = vC[k+1]
                
                y_k = filter_step(x_k, x_k1, x_k2, y_k1, y_k2)
                y_k2 = y_k1
                y_k1 = y_k
                
                e_k1 = e_k
                e_k = V_ref - y_k
                
                D_val = controller_step(e_k, e_k1, u_k1)
                
                if D_val > 1.0: D_val = 1.0
                elif D_val < 0.0: D_val = 0.0
                
                u_k1 = D_val
                
            D_array[k+1] = D_val

        # Cálculo do erro ignorando sinais menores que o limiar (ex: 1V para tensão, 0.05 para corrente/D)
        errors['vC'][method].append(calc_mape(vC, vC_qspice, threshold=1.0))
        errors['iL'][method].append(calc_mape(iL, iL_qspice, threshold=0.05))
        errors['D'][method].append(calc_mape(D_array, D_qspice, threshold=0.05))

# --- SALVAR RESULTADOS EM CSV ---
df_resultados = pd.DataFrame({
    'Fator_n': F_MULTIPLIERS,
    'Erro_vC_ZOH_percent': errors['vC']['zoh'],
    'Erro_iL_ZOH_percent': errors['iL']['zoh'],
    'Erro_D_ZOH_percent': errors['D']['zoh']
})

df_resultados.to_csv("resultados_erros_simulacao.csv", index=False)
print("Resultados salvos com sucesso em 'resultados_erros_simulacao.csv'")

# --- PLOTAGEM DOS ERROS ---
fig, (ax_iL, ax_vC) = plt.subplots(1, 2, figsize=(14, 6))

# Configuração visual para o ZOH
styles = {
    'zoh': {'marker': '^'}
}

# 1. Erro Tensão vC
for m in methods:
    ax_vC.plot(F_MULTIPLIERS, errors['vC'][m], marker=styles[m]['marker'], linestyle='-')
ax_vC.set_title('Tensão $v_C$', fontsize=FONT_TITLE)
ax_vC.set_xlabel('Fator n', fontsize=FONT_LABEL)
ax_vC.set_ylabel('Erro (%)', fontsize=FONT_LABEL)
ax_vC.tick_params(axis='both', labelsize=FONT_TICKS)
ax_vC.grid(True, which="both", ls="--", alpha=0.7)
ax_vC.set_xscale('log')
ax_vC.xaxis.set_major_formatter(ScalarFormatter()) 
ax_vC.set_xticks(ticks_to_show)
ax_vC.yaxis.set_major_locator(MaxNLocator(nbins=20))

# 2. Erro Corrente iL
for m in methods:
    ax_iL.plot(F_MULTIPLIERS, errors['iL'][m], marker=styles[m]['marker'], linestyle='-')
ax_iL.set_title('Corrente $i_L$', fontsize=FONT_TITLE)
ax_iL.set_xlabel('Fator n', fontsize=FONT_LABEL)
ax_iL.set_xticks(ticks_to_show)
ax_iL.set_ylabel('Erro (%)', fontsize=FONT_LABEL)
ax_iL.tick_params(axis='both', labelsize=FONT_TICKS)
ax_iL.set_xscale('log')
ax_iL.xaxis.set_major_formatter(ScalarFormatter())
ax_iL.grid(True, which="both", ls="--", alpha=0.7)
ax_iL.set_xticks(ticks_to_show)
ax_iL.yaxis.set_major_locator(MaxNLocator(nbins=20))

fig.tight_layout()
fig.savefig('erro_relativo.png', dpi=DPI)
plt.show()