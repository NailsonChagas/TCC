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
DPI = 500    

# Parâmetros do Circuito e Simulação
MAX_SIM_TIME = 6e-3 # Segundos (6 ms)
BASE_TIME_STEP = 1 / 50e3 
L = 1.5e-3
R = 41.7
C = 0.18e-6
V_S = 50
V_ref = 25

# Multiplicadores de Frequência (Escala logarítmica / Linear mista)
F_MULTIPLIERS = np.unique(np.concatenate([
    np.arange(1, 11, 1),
    np.arange(10, 101, 10),
    np.arange(100, 1001, 100),
    np.arange(1000, 10001, 1000)
]))

TARGET_PLOT_N = [10, 100, 1000, 10000] # Valores específicos para plotar os sinais

# ==========================================
# 2. FUNÇÕES AUXILIARES E SIMULAÇÃO
# ==========================================
def load_and_interpolate_data(filepath):
    """Lê os dados do QSPICE e retorna funções de interpolação."""
    df = pd.read_csv(filepath)
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

def simulate_buck_zoh(n, interp_vC, interp_iL, interp_D):
    """Roda a simulação ZOH para um dado multiplicador de frequência n."""
    timestep = BASE_TIME_STEP / n
    n_points = int(MAX_SIM_TIME / timestep)
    t_sim = np.arange(n_points) * timestep

    # CRIANDO O DEGRAU DE REFERÊNCIA:
    # Aos 3ms (3e-3 s), a referência sobe em 10V
    V_ref_array = np.where(t_sim >= 3e-3, V_ref + 10, V_ref)

    # Matrizes de Espaço de Estados (ZOH)
    A = np.array([[0, -1/L], [1/C, -1/(R*C)]])
    B1 = np.array([[1/L], [0]]) 
    B2 = np.array([[0], [0]]) 
    Ad = expm(A * timestep)
    A_inv = np.linalg.inv(A)
    Bd1 = A_inv @ (Ad - np.eye(2)) @ B1 
    Bd2 = A_inv @ (Ad - np.eye(2)) @ B2 

    # Sinais de referência no mesmo domínio de tempo (t_sim)
    vC_qspice = interp_vC(t_sim)
    iL_qspice = interp_iL(t_sim)
    D_qspice = interp_D(t_sim)

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
        is_sw_closed = (k % n) < (d_k * n)

        if is_sw_closed:
            iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k] + Bd1[0][0]*V_S
            vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k] + Bd1[1][0]*V_S
        else:
            iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k] + Bd2[0][0]*V_S
            vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k] + Bd2[1][0]*V_S

        if (k + 1) % n == 0:
            x_k2, x_k1, x_k = x_k1, x_k, vC[k+1]
            
            y_k = (1.0972729486243002 * y_k1 - 0.33759435110786473 * y_k2 + 
                   0.06008035062089115 * x_k + 0.1201607012417823 * x_k1 + 
                   0.06008035062089115 * x_k2)
            y_k2, y_k1 = y_k1, y_k
            
            # Atualização do Erro usando a referência dinâmica
            e_k1, e_k = e_k, V_ref_array[k+1] - y_k
            
            d_k = d_k1 + (0.001 + 32.5*BASE_TIME_STEP)*e_k + (32.5*BASE_TIME_STEP - 0.001)*e_k1
            d_k = np.clip(d_k, 0.0, 1.0) # Limita d_k entre 0 e 1
            d_k1 = d_k
            
        D_array[k+1] = d_k

    # Cálculo dos Erros MAPE
    mape_vC = calc_mape(vC, vC_qspice, threshold=0.05)
    mape_iL = calc_mape(iL, iL_qspice, threshold=0.05)
    mape_D = calc_mape(D_array, D_qspice, threshold=0.05)

    return (t_sim, vC, iL, D_array, vC_qspice, iL_qspice, D_qspice, V_ref_array), (mape_vC, mape_iL, mape_D)

# ==========================================
# 3. FUNÇÕES DE PLOTAGEM
# ==========================================

def plot_errors_vs_n(df):
    """Plota o comportamento dos erros MAPE em função do fator n."""
    plt.figure(figsize=(6, 5))
    plt.plot(df['Fator_n'], df['Erro_vC_ZOH_percent'], marker='o', label='Erro $v_C$ (%)')
    plt.plot(df['Fator_n'], df['Erro_iL_ZOH_percent'], marker='s', label='Erro $i_L$ (%)')
    plt.plot(df['Fator_n'], df['Erro_D_ZOH_percent'], marker='^', label='Erro D (%)')
    
    plt.xscale('log') 
    
    ax = plt.gca() 
    formatter = ScalarFormatter()
    formatter.set_scientific(False) 
    ax.xaxis.set_major_formatter(formatter)
    
    ax.set_xticks([1, 10, 100, 1000, 10000])
    
    plt.xlabel('Fator Multiplicador (n)', fontsize=FONT_LABEL)
    plt.ylabel('Erro MAPE (%)', fontsize=FONT_LABEL)
    plt.grid(True, which="both", ls="--", alpha=0.6)
    plt.legend(fontsize=FONT_LEGEND)
    plt.tight_layout()
    
    # Salva a imagem do erro
    plt.savefig("teste_erros_mape.png", dpi=DPI, bbox_inches='tight')
    plt.close()

def plot_signals_comparison(saved_signals):
    """
    Plota a comparação de vC, iL e D (Simulado vs QSPICE) para os valores escolhidos de n,
    dividindo em janelas de tempo específicas para melhor visualização dos transitórios.
    Gera imagens separadas em formato de grid 2x2 para cada valor de n.
    """
    # ---------------------------------------------------------
    # ADICIONADO UM NOVO INTERVALO PARA COMPLETAR O GRID 2x2
    # Altere o 3º elemento da lista conforme a sua necessidade
    # ---------------------------------------------------------
    figsize_aux = (10, 10)
    windows = [(0, 1), (2.5, 3), (3, 4), (0, 6)]
    window_titles = [
        'Transitório (0 a 1 ms)', 
        'Regime Permanente (2,5 a 3 ms)', 
        r'Degrau de $V_{ref}$: 25 V $\rightarrow$ 35 V ($3$ a $4$ ms)', 
        'Visão Geral (0 a 6 ms)'
    ]
    
    for n in TARGET_PLOT_N:
        if n not in saved_signals:
            continue
        
        data = saved_signals[n]
        t_ms = data['t'] * 1000 # Convertendo para ms
        
        # ==========================================
        # FIGURAS (2 linhas e 2 colunas para cada 'n')
        # ==========================================
        fig_vC, axes_vC = plt.subplots(nrows=2, ncols=2, figsize=figsize_aux)
        fig_iL, axes_iL = plt.subplots(nrows=2, ncols=2, figsize=figsize_aux)
        fig_D, axes_D = plt.subplots(nrows=2, ncols=2, figsize=figsize_aux)
        
        # O flatten() permite iterar sobre os 4 eixos como uma lista simples (0 a 3)
        axes_vC_flat = axes_vC.flatten()
        axes_iL_flat = axes_iL.flatten()
        axes_D_flat = axes_D.flatten()
        
        for j, window in enumerate(windows):
            # Calcula em qual linha e coluna estamos para formatar os rótulos corretamente
            row, col = divmod(j, 2) 
            
            # ---------------------------
            # Gráficos de Tensão (vC)
            # ---------------------------
            ax_vC = axes_vC_flat[j]
            ax_vC.plot(t_ms, data['vC_qspice'], label='QSPICE', color='black', alpha=0.6)
            ax_vC.plot(t_ms, data['vC'], label=f'ZOH', color='tab:blue')
            
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
            ax_iL.plot(t_ms, data['iL_qspice'], label='QSPICE', color='black', alpha=0.6)
            ax_iL.plot(t_ms, data['iL'], label=f'ZOH', color='tab:red')
            
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
            ax_D.plot(t_ms, data['D_qspice'], label='QSPICE', color='black', alpha=0.6, lw=2)
            ax_D.plot(t_ms, data['D'], label=f'ZOH', color='tab:green', lw=1.5)
            
            ax_D.set_xlim(window)
            ax_D.grid(True, alpha=0.5, linestyle='--')
            ax_D.set_title(window_titles[j], fontsize=FONT_TITLE)
            
            if row == 1: ax_D.set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
            if col == 0: ax_D.set_ylabel('$D$', fontsize=FONT_LABEL)
            if j == 3: ax_D.legend(loc='lower right', fontsize=FONT_LEGEND)

        # Ajuste de layout 
        fig_vC.tight_layout()
        fig_iL.tight_layout()
        fig_D.tight_layout()
        
        # Salva as imagens (o sufixo com 'n' garante que não haverá sobrescrita)
        fig_vC.savefig(f"teste_comparacao_vC_n{n}.png", dpi=DPI, bbox_inches='tight')
        fig_iL.savefig(f"teste_comparacao_iL_n{n}.png", dpi=DPI, bbox_inches='tight')
        fig_D.savefig(f"teste_comparacao_D_n{n}.png", dpi=DPI, bbox_inches='tight')
        plt.close('all')

# ==========================================
# 4. ROTINA PRINCIPAL (MAIN)
# ==========================================
if __name__ == "__main__":
    # 1. Carregar Dados do QSpice
    interp_vC, interp_iL, interp_D = load_and_interpolate_data("buck_filtro_controle3.csv")

    errors_dict = {'vC': [], 'iL': [], 'D': []}
    saved_signals = {}

    print("Iniciando varredura de simulações...")
    for n in F_MULTIPLIERS:
        # 2. Rodar Simulação
        signals, mapes = simulate_buck_zoh(n, interp_vC, interp_iL, interp_D)
        
        # 3. Armazenar Erros
        errors_dict['vC'].append(mapes[0])
        errors_dict['iL'].append(mapes[1])
        errors_dict['D'].append(mapes[2])

        # 4. Salvar sinais específicos num dicionário e também em arquivos CSV
        if n in TARGET_PLOT_N:
            # Salva na memória para o plot (Agora com o D incluído)
            saved_signals[n] = {
                't': signals[0],
                'vC': signals[1], 'iL': signals[2], 'D': signals[3],
                'vC_qspice': signals[4], 'iL_qspice': signals[5], 'D_qspice': signals[6],
                'V_ref': signals[7]
            }
            
            # --- EXPORTANDO OS SINAIS PARA CSV ---
            df_sinais = pd.DataFrame({
                'Time': signals[0],
                'vC_ZOH': signals[1],
                'iL_ZOH': signals[2],
                'D_ZOH': signals[3],
                'vC_QSPICE': signals[4],
                'iL_QSPICE': signals[5],
                'D_QSPICE': signals[6],
                'V_ref': signals[7]
            })
            
            nome_arquivo = f"sinais_comparacao_n{n}.csv"
            df_sinais.to_csv(nome_arquivo, index=False)
            print(f" -> Sinais exportados: {nome_arquivo}")

    # 5. Salvar Resultados dos Erros MAPE em CSV
    df_resultados = pd.DataFrame({
        'Fator_n': F_MULTIPLIERS,
        'Erro_vC_ZOH_percent': errors_dict['vC'],
        'Erro_iL_ZOH_percent': errors_dict['iL'],
        'Erro_D_ZOH_percent': errors_dict['D']
    })
    df_resultados.to_csv("resultados_erros_simulacao.csv", index=False)
    print("\nResultados de erros salvos com sucesso em 'resultados_erros_simulacao.csv'")

    # 6. Gerar Gráficos e Salvar
    print("Gerando gráficos e salvando imagens...")
    plot_errors_vs_n(df_resultados)
    plot_signals_comparison(saved_signals)