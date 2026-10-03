import numpy as np
import matplotlib.pyplot as plt
from scipy.linalg import expm
import matplotlib.gridspec as gridspec
import pandas as pd
import os

# ==========================================================
# VARIÁVEIS DE CONFIGURAÇÃO DE FONTES E PLOTAGEM
# ==========================================================
FONT_TITLE = 15    
FONT_LABEL = 11    
FONT_TICKS = 10    
FONT_LEGEND = 10 
DPI = 150         

# ==========================================================
# PARÂMETROS DO CONVERSOR BUCK E SIMULAÇÃO
# ==========================================================
Vs = 50         # Tensão de entrada [V]
Fs = 5e3         # Frequência de chaveamento [Hz]
D = 0.50         # Razão cíclica [adimensional]
L = 12.5e-3      # Indutância [H]
R = 6.25         # Resistência de carga [Ohm]
C = 50e-6        # Capacitância [F]
Ts = 1 / Fs

F_MULTIPLIER = [100]
T_END = 0.080    # tempo total da simulação (80ms)

# ==========================================================
# FUNÇÃO DE DISCRETIZAÇÃO (ZOH)
# ==========================================================
def buck_zoh_discretization(n):
    Tsim = 1 / (n * Fs)
    n_points = int(T_END / Tsim)

    # Matrizes de Espaço de Estados (Contínuas)
    A = np.array([[0, -1/L], 
                 [1/C, -1/(R*C)]])
    B1 = np.array([1/L, 0])
    
    # Matrizes ZOH (Discretas)
    Ad = expm(A * Tsim)
    A_inv = np.linalg.inv(A)
    Bd1 = A_inv @ (Ad - np.eye(2)) @ B1  

    iL = np.zeros(n_points)
    vC = np.zeros(n_points)
    t = np.linspace(0, T_END, n_points)

    for k in range(n_points - 1):
        if (t[k] % Ts) < (D * Ts): # chave fechada
            iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k] + Bd1[0]*Vs
            vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k] + Bd1[1]*Vs
        else: # chave aberta
            iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k]
            vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k]

    return t, iL, vC

def gerar_painel_variavel_horizontal(resultados_sim, t_qs, var_qs, nome_var, ylabel, filename):
    """
    Gera uma única imagem contendo 3 subplots dispostos em 2 linhas:
    - Linha 1: Regime Transitório e Regime Permanente (2 colunas)
    - Linha 2: Visão Geral centralizada (ocupando a largura total)
    """
    fig = plt.figure(figsize=(9, 8))
    gs = gridspec.GridSpec(2, 2, figure=fig)
    
    # Ordem alterada: Linha 0 (topo) recebe Transitório e Permanente. Linha 1 (baixo) recebe Visão Geral.
    ax_trans = fig.add_subplot(gs[0, 0])
    ax_perm  = fig.add_subplot(gs[0, 1])
    ax_geral = fig.add_subplot(gs[1, :])  # Ocupa toda a linha inferior
    
    sub_configs = [
        (ax_trans, f'Regime Transitório', (0.0, 10)),
        (ax_perm,  f'Regime Permanente', (40, 50)),
        (ax_geral, f'Visão Geral', None)
    ]

    qs_style = {'color': 'black', 'linewidth': 1.1, 'linestyle': '-', 'alpha': 0.5, 'label': 'QSpice'}

    for i, (ax, titulo, xlim) in enumerate(sub_configs):
        # Plota QSpice de referência
        ax.plot(t_qs * 1000, var_qs, **qs_style)
        
        # Plota simulações ZOH
        for n in sorted(resultados_sim.keys()):
            dados = resultados_sim[n]
            ax.plot(dados['t_zoh'] * 1000, dados[f'{nome_var}_zoh'], label=f'n={n}', alpha=0.8)
            
        # Aplica o ylabel 
        ax.set_ylabel(ylabel, fontsize=FONT_LABEL)
            
        ax.set_xlabel('Tempo [ms]', fontsize=FONT_LABEL)
        ax.set_title(titulo, fontsize=FONT_TITLE)
        ax.grid(True)
        ax.tick_params(axis='both', labelsize=FONT_TICKS)
        
        if xlim:
            ax.set_xlim(xlim)
            
        # Legenda compacta em duas colunas para otimizar espaço
        ax.legend(loc='lower right', fontsize=FONT_LEGEND, ncol=2)

    fig.tight_layout()
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    fig.savefig(filename, dpi=DPI)
    plt.close(fig)
    print(f"Imagem '{filename}' salva com sucesso!")

# ==========================================================
# FUNÇÃO PRINCIPAL (ORQUESTRADOR)
# ==========================================================
def main():
    try:
        df_qs = pd.read_csv('buck.csv', sep=None, engine='python')
        df_qs.columns = df_qs.columns.str.strip() 
        
        t_qs = df_qs["Time"].values  
        iL_qs = df_qs["I(L1)"].values  
        vC_qs = df_qs["V(buck)"].values  
    except FileNotFoundError:
        print("Arquivo 'buck.csv' não encontrado. Certifique-se de que ele está na mesma pasta.")
        return
    except KeyError as e:
        print(f"Erro: A coluna {e} não foi encontrada no cabeçalho do arquivo CSV.")
        print("Colunas disponíveis no arquivo:", list(df_qs.columns))
        return

    # Execução das Simulações ZOH
    resultados_sim = {}
    for n in F_MULTIPLIER:
        t_zoh, iL_zoh, vC_zoh = buck_zoh_discretization(n)
        resultados_sim[n] = {
            't_zoh': t_zoh, 'iL_zoh': iL_zoh, 'vC_zoh': vC_zoh
        }

    # 2. Gera imagem de Corrente
    gerar_painel_variavel_horizontal(
        resultados_sim=resultados_sim,
        t_qs=t_qs,
        var_qs=iL_qs,
        nome_var='iL',
        ylabel=r'$i_L$ [A]',
        filename='img/reprojeto_corrente_zoh.png',
    )

    # 3. Gera imagem de Tensão
    gerar_painel_variavel_horizontal(
        resultados_sim=resultados_sim,
        t_qs=t_qs,
        var_qs=vC_qs,
        nome_var='vC',
        ylabel=r'$v_C$ [V]',
        filename='img/reprojeto_tensao_zoh.png',
    )

    print("Processo concluído! As imagens foram geradas com a nova ordem de subplots.")

if __name__ == "__main__":
    main()