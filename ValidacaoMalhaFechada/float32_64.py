import numpy as np
import pandas as pd
from scipy.linalg import expm
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

# ==========================================
# 1. CONSTANTES E CONFIGURAÇÕES
# ==========================================
# Configurações de Gráficos
FONT_TITLE = 16    
FONT_LABEL = 13    
FONT_TICKS = 12    
FONT_LEGEND = 13 
DPI = 200    

# Parâmetros do Circuito e Simulação
MAX_SIM_TIME = 6e-3 # Segundos (6 ms)
BASE_TIME_STEP = 1 / 50e3 
L = 1.5e-3
R = 41.7
C = 0.18e-6
V_S = 50
V_ref = 25

# Fator N fixo em 100
N_SIM = 100 

# ==========================================
# 2. FUNÇÕES AUXILIARES E SIMULAÇÃO
# ==========================================
def load_and_interpolate_data(filepath):
    """Lê os dados do QSPICE e retorna funções de interpolação."""
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"ATENÇÃO: Arquivo {filepath} não encontrado! Crie dados falsos para evitar quebrar o script (Apenas p/ teste).")
        t_f = np.linspace(0, MAX_SIM_TIME, 10000)
        df = pd.DataFrame({'Time': t_f, 'V(buck)': 25*np.ones_like(t_f), 'I(L1)': 0.6*np.ones_like(t_f), 'V(duty_cycle)': 0.5*np.ones_like(t_f)})
        
    t_qspice = df['Time'].values
    vC_qspice_data = df['V(buck)'].values
    iL_qspice_data = df['I(L1)'].values
    D_qspice_data = df['V(duty_cycle)'].values
    
    interp_vC = interp1d(t_qspice, vC_qspice_data, fill_value="extrapolate")
    interp_iL = interp1d(t_qspice, iL_qspice_data, fill_value="extrapolate")
    interp_D = interp1d(t_qspice, D_qspice_data, kind='previous', fill_value="extrapolate")
    
    return interp_vC, interp_iL, interp_D

def calc_mape(sim, ref, threshold=0.05):
    """Calcula o Erro Percentual Absoluto Médio (MAPE) ignorando valores próximos a zero."""
    mask = np.abs(ref) > threshold
    if np.sum(mask) == 0: return 0.0
    return np.mean(np.abs(sim[mask] - ref[mask]) / np.abs(ref[mask])) * 100

def simulate_buck_zoh(n, interp_vC, interp_iL, interp_D, n_points_fixed=None, dtype=np.float64):
    """
    Roda a simulação ZOH forçando as contas para a precisão do tipo `dtype`.
    Se `n_points_fixed` for fornecido, garante exatamente o mesmo número de pontos.
    """
    timestep = dtype(BASE_TIME_STEP / n)
    
    if n_points_fixed is not None:
        n_points = n_points_fixed
    else:
        n_points = int(np.round(MAX_SIM_TIME / float(timestep)))
    
    # Casting do vetor de tempo e referência
    t_sim = (np.arange(n_points) * timestep).astype(dtype)
    V_ref_array = np.where(t_sim >= 3e-3, dtype(V_ref + 10), dtype(V_ref)).astype(dtype)

    # Matrizes de Espaço de Estados
    A = np.array([[0, -1/L], [1/C, -1/(R*C)]], dtype=dtype)
    B1 = np.array([[1/L], [0]], dtype=dtype) 
    B2 = np.array([[0], [0]], dtype=dtype) 
    
    Ad_64 = expm(A * (BASE_TIME_STEP / n))
    A_inv_64 = np.linalg.inv(A)
    Bd1_64 = A_inv_64 @ (Ad_64 - np.eye(2)) @ B1 
    Bd2_64 = A_inv_64 @ (Ad_64 - np.eye(2)) @ B2 
    
    Ad = Ad_64.astype(dtype)
    Bd1 = Bd1_64.astype(dtype)
    Bd2 = Bd2_64.astype(dtype)
    V_S_typed = dtype(V_S)

    vC_qspice = interp_vC(np.float64(t_sim))
    iL_qspice = interp_iL(np.float64(t_sim))
    D_qspice = interp_D(np.float64(t_sim))

    iL = np.zeros(n_points, dtype=dtype)
    vC = np.zeros(n_points, dtype=dtype)
    D_array = np.zeros(n_points, dtype=dtype)

    e_k = dtype(0.0); e_k1 = dtype(0.0)
    d_k = dtype(0.0); d_k1 = dtype(0.0)
    x_k = dtype(0.0); x_k1 = dtype(0.0); x_k2 = dtype(0.0)
    y_k = dtype(0.0); y_k1 = dtype(0.0); y_k2 = dtype(0.0)

    c_y1 = dtype(1.0972729486243002)
    c_y2 = dtype(-0.33759435110786473)
    c_x0 = dtype(0.06008035062089115)
    c_x1 = dtype(0.1201607012417823)
    c_x2 = dtype(0.06008035062089115)
    
    c_e0 = dtype(0.001 + 32.5*BASE_TIME_STEP)
    c_e1 = dtype(32.5*BASE_TIME_STEP - 0.001)

    for k in range(n_points - 1):
        is_sw_closed = (k % n) < (float(d_k) * n)

        if is_sw_closed:
            iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k] + Bd1[0,0]*V_S_typed
            vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k] + Bd1[1,0]*V_S_typed
        else:
            iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k] + Bd2[0,0]*V_S_typed
            vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k] + Bd2[1,0]*V_S_typed

        if (k + 1) % n == 0:
            x_k2, x_k1, x_k = x_k1, x_k, vC[k+1]
            
            y_k = (c_y1 * y_k1 + c_y2 * y_k2 + 
                   c_x0 * x_k  + c_x1 * x_k1 + c_x2 * x_k2)
            y_k2, y_k1 = y_k1, y_k
            
            e_k1, e_k = e_k, V_ref_array[k+1] - y_k
            
            d_k = d_k1 + c_e0 * e_k + c_e1 * e_k1
            
            if d_k > dtype(1.0): d_k = dtype(1.0)
            elif d_k < dtype(0.0): d_k = dtype(0.0)
            
            d_k1 = d_k
            
        D_array[k+1] = d_k

    mape_vC = calc_mape(vC, vC_qspice, threshold=0.05)
    mape_iL = calc_mape(iL, iL_qspice, threshold=0.05)
    mape_D = calc_mape(D_array, D_qspice, threshold=0.05)

    return (t_sim, vC, iL, D_array, vC_qspice, iL_qspice, D_qspice, V_ref_array), (mape_vC, mape_iL, mape_D)

# ==========================================
# 3. FUNÇÕES DE PLOTAGEM
# ==========================================
def plot_signals_comparison(sim_32, sim_64):
    """
    Plota a comparação de vC, iL e D (QSPICE vs Float64 vs Float32).
    """
    figsize_aux = (11, 10) # Um pouco mais largo para acomodar bem as legendas duplas
    windows = [(0, 1), (2.5, 3), (3, 4), (0, 6)]
    window_titles = [
        'Regime Transitório', 
        'Regime Permanente', 
        r'Degrau de $V_{ref}$: 25 V $\rightarrow$ 35 V', 
        'Visão Geral'
    ]
    
    # Extração das matrizes (usamos a matriz de tempo do float64 como base de plotagem, a diferença é ínfima)
    t_ms = sim_64[0] * 1000 
    
    fig_vC, axes_vC = plt.subplots(nrows=2, ncols=2, figsize=figsize_aux)
    fig_iL, axes_iL = plt.subplots(nrows=2, ncols=2, figsize=figsize_aux)
    fig_D,  axes_D  = plt.subplots(nrows=2, ncols=2, figsize=figsize_aux)
    
    axes_vC_flat = axes_vC.flatten()
    axes_iL_flat = axes_iL.flatten()
    axes_D_flat  = axes_D.flatten()
    
    for j, window in enumerate(windows):
        row, col = divmod(j, 2) 
        
        # ---------------------------
        # Gráficos de Tensão (vC)
        # ---------------------------
        ax_vC = axes_vC_flat[j]
        ax_vC.plot(t_ms, sim_64[4], label='QSPICE', color='black', alpha=0.5, lw=2.5)
        ax_vC.plot(t_ms, sim_64[1], label='ZOH (float64)', color='tab:blue')
        ax_vC.plot(t_ms, sim_32[1], label='ZOH (float32)', color='tab:red', linestyle='--')
        
        ax_vC.set_xlim(window)
        ax_vC.grid(True, alpha=0.5, linestyle='--')
        ax_vC.set_title(window_titles[j], fontsize=FONT_TITLE)
        
        if row == 1: ax_vC.set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
        if col == 0: ax_vC.set_ylabel('$v_C$ (V)', fontsize=FONT_LABEL)
        if j == 3: ax_vC.legend(loc='lower right', fontsize=FONT_LEGEND)

        # ---------------------------
        # Gráficos de Corrente (iL)
        # ---------------------------
        ax_iL = axes_iL_flat[j]
        ax_iL.plot(t_ms, sim_64[5], label='QSPICE', color='black', alpha=0.5, lw=2.5)
        ax_iL.plot(t_ms, sim_64[2], label='ZOH (float64)', color='tab:blue')
        ax_iL.plot(t_ms, sim_32[2], label='ZOH (float32)', color='tab:red', linestyle='--')
        
        ax_iL.set_xlim(window)
        ax_iL.grid(True, alpha=0.5, linestyle='--')
        ax_iL.set_title(window_titles[j], fontsize=FONT_TITLE)
        
        if row == 1: ax_iL.set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
        if col == 0: ax_iL.set_ylabel('$i_L$ (A)', fontsize=FONT_LABEL)
        if j == 3: ax_iL.legend(loc='lower right', fontsize=FONT_LEGEND)

        # ---------------------------
        # Gráficos de Duty Cycle (D)
        # ---------------------------
        ax_D = axes_D_flat[j]
        ax_D.plot(t_ms, sim_64[6], label='QSPICE', color='black', alpha=0.5, lw=2.5)
        ax_D.plot(t_ms, sim_64[3], label='ZOH (float64)', color='tab:blue')
        ax_D.plot(t_ms, sim_32[3], label='ZOH (float32)', color='tab:red', linestyle='--')
        
        ax_D.set_xlim(window)
        ax_D.grid(True, alpha=0.5, linestyle='--')
        ax_D.set_title(window_titles[j], fontsize=FONT_TITLE)
        
        if row == 1: ax_D.set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
        if col == 0: ax_D.set_ylabel('$D$', fontsize=FONT_LABEL)
        if j == 3: ax_D.legend(loc='lower right', fontsize=FONT_LEGEND)

    fig_vC.tight_layout()
    fig_iL.tight_layout()
    fig_D.tight_layout()
    
    fig_vC.savefig(f"teste_comparacao_vC_float32_vs_64.png", dpi=DPI, bbox_inches='tight')
    fig_iL.savefig(f"teste_comparacao_iL_float32_vs_64.png", dpi=DPI, bbox_inches='tight')
    fig_D.savefig(f"teste_comparacao_D_float32_vs_64.png", dpi=DPI, bbox_inches='tight')
    plt.close('all')

# ==========================================
# 4. ROTINA PRINCIPAL (MAIN)
# ==========================================
if __name__ == "__main__":
    interp_vC, interp_iL, interp_D = load_and_interpolate_data("buck_filtro_controle3.csv")

    print(f"Iniciando simulações para n={N_SIM}...")
    
    # 2. Rodar Simulação Float64
    print(" -> Simulando com precisão float64 (Alta Precisão)...")
    sim_64, mapes_64 = simulate_buck_zoh(N_SIM, interp_vC, interp_iL, interp_D, dtype=np.float64)
    
    # Captura o número exato de pontos gerados na referência Float64
    n_points_exact = len(sim_64[0])

    # 3. Rodar Simulação Float32 com o mesmo tamanho de vetor
    print(" -> Simulando com precisão float32 (MCU Simulação)...")
    sim_32, mapes_32 = simulate_buck_zoh(N_SIM, interp_vC, interp_iL, interp_D, n_points_fixed=n_points_exact, dtype=np.float32)

    # 4. Exibir resultados de erro
    print("\n================ RESULTADOS MAPE (vs QSPICE) ================")
    print(f"[Float64] Erros -> vC: {mapes_64[0]:.4f}% | iL: {mapes_64[1]:.4f}% | D: {mapes_64[2]:.4f}%")
    print(f"[Float32] Erros -> vC: {mapes_32[0]:.4f}% | iL: {mapes_32[1]:.4f}% | D: {mapes_32[2]:.4f}%")
    
    diff_vC_max = np.max(np.abs(sim_64[1] - sim_32[1]))
    diff_iL_max = np.max(np.abs(sim_64[2] - sim_32[2]))
    print(f"Diferença Máxima (F64 vs F32) -> vC: {diff_vC_max:.6e} V | iL: {diff_iL_max:.6e} A")
    print("=============================================================\n")

    # 5. Exportando para CSV (Dados consolidados)
    df_sinais = pd.DataFrame({
        'Time': sim_64[0],
        'vC_ZOH_Float64': sim_64[1],
        'iL_ZOH_Float64': sim_64[2],
        'D_ZOH_Float64': sim_64[3],
        'vC_ZOH_Float32': sim_32[1],
        'iL_ZOH_Float32': sim_32[2],
        'D_ZOH_Float32': sim_32[3],
        'vC_QSPICE': sim_64[4],
        'iL_QSPICE': sim_64[5],
        'D_QSPICE': sim_64[6],
        'V_ref': sim_64[7]
    })
    
    nome_arquivo = f"sinais_comparacao_float32_vs_float64_n{N_SIM}.csv"
    df_sinais.to_csv(nome_arquivo, index=False)
    print(f"Dados exportados para: {nome_arquivo}")

    # 6. Gerar Gráficos e Salvar
    print("Gerando gráficos e salvando imagens...")
    plot_signals_comparison(sim_32, sim_64)
    print("Concluído!")