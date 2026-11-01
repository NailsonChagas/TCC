import numpy as np
import pandas as pd
from scipy.linalg import expm
import matplotlib.pyplot as plt

# ==========================================
# 1. CONSTANTES E CONFIGURAÇÕES
# ==========================================
FONT_TITLE = 16    
FONT_LABEL = 13    
FONT_TICKS = 12    
FONT_LEGEND = 13 
DPI = 200    

# Parâmetros do Circuito e Simulação
MAX_SIM_TIME = 60.0  # 60 segundos (60000 ms)
BASE_TIME_STEP = 1 / 5e3 
L = 12500e-6
R = 6.25
C = 50e-6
V_S = 50
V_ref = 25

# Tempos dos Eventos (em Segundos)
CONTROLLER_ON_TIME = 1.0734520   # 1073.4520 ms
VREF_STEP_TIME = 30.2689620      # 30268.9620 ms
VREF_STEP_ADD = 10

F_MULTIPLIERS = [100]

# ==========================================
# 2. FUNÇÃO DE SIMULAÇÃO (PURA)
# ==========================================
def simulate_buck_zoh(n):
    """Roda a simulação ZOH para um dado multiplicador de frequência n."""
    timestep = BASE_TIME_STEP / n
    n_points = int(MAX_SIM_TIME / timestep)
    t_sim = np.arange(n_points) * timestep

    # Degrau da referência
    V_ref_array = np.where(t_sim >= VREF_STEP_TIME, V_ref + VREF_STEP_ADD, V_ref)

    # Matrizes de Espaço de Estados (ZOH)
    A = np.array([[0, -1/L], [1/C, -1/(R*C)]])
    B1 = np.array([[1/L], [0]]) 
    B2 = np.array([[0], [0]]) 
    Ad = expm(A * timestep)
    A_inv = np.linalg.inv(A)
    Bd1 = A_inv @ (Ad - np.eye(2)) @ B1 
    Bd2 = A_inv @ (Ad - np.eye(2)) @ B2 

    # Inicialização dos vetores
    iL = np.zeros(n_points)
    vC = np.zeros(n_points)
    D_array = np.zeros(n_points)

    # Variáveis de estado do controlador e filtro
    e_k = e_k1 = 0.0 
    d_k = d_k1 = 0.0 
    x_k = x_k1 = x_k2 = 0.0 
    y_k = y_k1 = y_k2 = 0.0 

    for k in range(n_points - 1):
        if k % 10000 == 0:
            print(f"Simulando: {k} de {n_points - 1}")
        
        is_sw_closed = (k % n) < (d_k * n)

        # Atualização da planta (Conversor Buck)
        if is_sw_closed:
            iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k] + Bd1[0][0]*V_S
            vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k] + Bd1[1][0]*V_S
        else:
            iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k] + Bd2[0][0]*V_S
            vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k] + Bd2[1][0]*V_S

        # Lógica Digital (Filtro e Controlador)
        if (k + 1) % n == 0:
            x_k2, x_k1, x_k = x_k1, x_k, vC[k+1]

            y_k = (1.0972729486243 * y_k1 - 0.3375943511078646 * y_k2 + 
                   0.06008035062089116 * x_k + 0.12016070124178233 * x_k1 + 
                   0.06008035062089116 * x_k2)
            y_k2, y_k1 = y_k1, y_k
            
            e_k1, e_k = e_k, V_ref_array[k+1] - y_k
            
            # Condição para ativar o controlador
            if t_sim[k+1] >= CONTROLLER_ON_TIME:
                d_k = 1.000000 * d_k1 + 0.00035771900000000005 * e_k + 0.00034688100000000006 * e_k1
                d_k = np.clip(d_k, 0.0, 1.0)
            else:
                d_k = 0.0
                
            d_k1 = d_k
            
        D_array[k+1] = d_k

    return t_sim, vC, iL, D_array, V_ref_array

# ==========================================
# 3. FUNÇÃO DE PLOTAGEM
# ==========================================
def plot_simulation_signals(saved_signals, t_ligado, t_degrau):
    figsize_aux = (10, 10)
    
    for n, data in saved_signals.items():
        t_ms = data['t'] * 1000 # Convertendo para ms
        t_max = t_ms.max()
        
        # ==========================================
        # DEFINIÇÃO DINÂMICA DAS JANELAS E TÍTULOS
        # ==========================================
        windows = [
            (t_ligado - 20, t_ligado + 80),                # Janela de 100ms em torno do controlador ligado
            (t_ligado + 80, t_ligado + (80*2)),   
            (t_degrau - 50, t_degrau + 150),               # Janela de 200ms em torno do degrau
            (0, t_max)                                     # Visão Geral dinâmica
        ]
        
        window_titles = [
            'Ativação do Controlador', 
            'Regime Permanente', 
            rf'Degrau de $V_{{ref}}$', 
            'Visão Geral'
        ]
        
        fig_vC, axes_vC = plt.subplots(nrows=2, ncols=2, figsize=figsize_aux)
        fig_iL, axes_iL = plt.subplots(nrows=2, ncols=2, figsize=figsize_aux)
        fig_D, axes_D = plt.subplots(nrows=2, ncols=2, figsize=figsize_aux)
        
        axes_vC_flat = axes_vC.flatten()
        axes_iL_flat = axes_iL.flatten()
        axes_D_flat = axes_D.flatten()
        
        for j, window in enumerate(windows):
            row, col = divmod(j, 2) 
            
            # Tensão (vC) e Referência
            ax_vC = axes_vC_flat[j]
            ax_vC.plot(t_ms, data['vC'], label='vC (ZOH)', color='tab:blue')
            ax_vC.set_xlim(window)
            ax_vC.grid(True, alpha=0.5, linestyle='--')
            ax_vC.set_title(window_titles[j], fontsize=FONT_TITLE)
            if row == 1: ax_vC.set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
            if col == 0: ax_vC.set_ylabel('Tensão (V)', fontsize=FONT_LABEL)
            if j == 3: ax_vC.legend(loc='lower right', fontsize=FONT_LEGEND)

            # Corrente (iL)
            ax_iL = axes_iL_flat[j]
            ax_iL.plot(t_ms, data['iL'], label='iL (ZOH)', color='tab:red')
            ax_iL.set_xlim(window)
            ax_iL.grid(True, alpha=0.5, linestyle='--')
            ax_iL.set_title(window_titles[j], fontsize=FONT_TITLE)
            if row == 1: ax_iL.set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
            if col == 0: ax_iL.set_ylabel('Corrente (A)', fontsize=FONT_LABEL)
            if j == 3: ax_iL.legend(loc='lower right', fontsize=FONT_LEGEND)

            # Duty Cycle (D)
            ax_D = axes_D_flat[j]
            ax_D.plot(t_ms, data['D'], label='D (ZOH)', color='tab:green', lw=1.5)
            ax_D.set_xlim(window)
            ax_D.grid(True, alpha=0.5, linestyle='--')
            ax_D.set_title(window_titles[j], fontsize=FONT_TITLE)
            if row == 1: ax_D.set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
            if col == 0: ax_D.set_ylabel('Duty Cycle (D)', fontsize=FONT_LABEL)
            if j == 3: ax_D.legend(loc='lower right', fontsize=FONT_LEGEND)

        fig_vC.tight_layout()
        fig_iL.tight_layout()
        fig_D.tight_layout()
        
        fig_vC.savefig(f"simulacao_vC_n{n}.png", dpi=DPI, bbox_inches='tight')
        fig_iL.savefig(f"simulacao_iL_n{n}.png", dpi=DPI, bbox_inches='tight')
        fig_D.savefig(f"simulacao_D_n{n}.png", dpi=DPI, bbox_inches='tight')
        plt.close('all')

# ==========================================
# 4. ROTINA PRINCIPAL (MAIN)
# ==========================================
if __name__ == "__main__":
    saved_signals = {}

    print("Iniciando varredura de simulações...")
    for n in F_MULTIPLIERS:
        print(f"A simular o modelo ZOH para n={n}...")
        t_sim, vC, iL, D_array, V_ref_array = simulate_buck_zoh(n)
        
        saved_signals[n] = {
            't': t_sim,
            'vC': vC, 'iL': iL, 'D': D_array, 'V_ref': V_ref_array
        }
        
        # --- EXPORTANDO OS SINAIS PARA CSV ---
        df_sinais = pd.DataFrame({
            'Time': t_sim,
            'vC': vC,
            'iL': iL,
            'D': D_array,
            'V_ref': V_ref_array
        })
        
        nome_arquivo = f"sinais_simulados_n{n}.csv"
        df_sinais.to_csv(nome_arquivo, index=False)
        print(f" -> Sinais exportados: {nome_arquivo}")

    print("Gerando gráficos e salvando imagens...")
    plot_simulation_signals(
        saved_signals, 
        t_ligado=CONTROLLER_ON_TIME * 1000, 
        t_degrau=VREF_STEP_TIME * 1000
    )
    print("Processo concluído.")