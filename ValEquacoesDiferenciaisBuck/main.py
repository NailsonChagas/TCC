import numpy as np
import matplotlib.pyplot as plt
  
# ==========================================================
# VARIÁVEIS DE CONFIGURAÇÃO DE FONTES E PLOTAGEM
# ==========================================================
FONT_TITLE = 15    
FONT_LABEL = 13    
FONT_TICKS = 12    
FONT_LEGEND = 13 
DPI = 500          

# ==========================================================
# PARÂMETROS DO CONVERSOR BUCK E SIMULAÇÃO
# ==========================================================
Vs = 50          # Tensão de entrada [V]
Fs = 50e3        # Frequência de chaveamento [Hz]
D = 0.50         # Razão cíclica [adimensional]
L = 1.5e-3       # Indutância [H]
R = 41.7         # Resistência de carga [Ohm]
C = 0.18e-6      # Capacitância [F]
Ts = 1 / Fs

F_MULTIPLIER = [5, 10, 20, 30, 40, 50, 100]
T_END = 0.0010   # tempo total da simulação (1ms)

# ==========================================================
# FUNÇÕES DE DISCRETIZAÇÃO
# ==========================================================
def buck_euler_discretization(n):
    Tsim = 1 / (n * Fs)
    n_points = int(T_END / Tsim)

    ke1 = Tsim / L
    ke2 = Tsim / C
    ke3 = 1 - (Tsim / (R * C))

    iL = np.zeros(n_points)
    vC = np.zeros(n_points)
    t = np.linspace(0, T_END, n_points)

    for k in range(n_points - 1):
        if (t[k] % Ts) < (D * Ts): # chave fechada
            iL[k+1] = iL[k] - ke1 * vC[k] + ke1 * Vs
            vC[k+1] = ke2 * iL[k] + ke3 * vC[k]
        else: # chave aberta
            iL[k+1] = iL[k] - ke1 * vC[k]
            vC[k+1] = ke2 * iL[k] + ke3 * vC[k]

    return t, iL, vC

def buck_trapezium_discretization(n):
    Tsim = 1 / (n * Fs)
    n_points = int(T_END / Tsim)

    Delta = 4*C*L*R + 2*L*Tsim + R*(Tsim**2)    
    kt1 = (4*C*L*R + 2*L*Tsim - R*(Tsim**2)) / Delta
    kt2 = (4*C*R*Tsim) / Delta
    kt3 = (Tsim**2 + 2*C*R*Tsim) / Delta
    kt4 = (4*L*R*Tsim) / Delta
    kt5 = (4*C*L*R - 2*L*Tsim - R*(Tsim**2)) / Delta
    kt6 = (R*(Tsim**2)) / Delta

    iL = np.zeros(n_points)
    vC = np.zeros(n_points)
    t = np.linspace(0, T_END, n_points)

    for k in range(n_points - 1):
        if (t[k] % Ts) < (D * Ts): # chave fechada
            iL[k+1] = kt1 * iL[k] - kt2 * vC[k] + kt3 * (2 * Vs)
            vC[k+1] = kt4 * iL[k] + kt5 * vC[k] + kt6 * (2 * Vs)
        else: # chave aberta
            iL[k+1] = kt1 * iL[k] - kt2 * vC[k]
            vC[k+1] = kt4 * iL[k] + kt5 * vC[k]

    return t, iL, vC

# ==========================================================
# FUNÇÕES DE CÁLCULO E PLOTAGEM
# ==========================================================
def plot_erro_relativo_medio(resultados_sim, t_qs, iL_qs, vC_qs):
    err_iL_eul, err_vC_eul = [], []
    err_iL_trap, err_vC_trap = [], []
    
    n_sorted = sorted(resultados_sim.keys())
    eps = 1e-8 # Evitar divisão por zero
    
    for n in n_sorted:
        dados = resultados_sim[n]
        
        # Interpolação Euler
        iL_qs_interp_eul = np.interp(dados['t_eul'], t_qs, iL_qs)
        vC_qs_interp_eul = np.interp(dados['t_eul'], t_qs, vC_qs)
        
        # Interpolação Trapézio
        iL_qs_interp_trap = np.interp(dados['t_trap'], t_qs, iL_qs)
        vC_qs_interp_trap = np.interp(dados['t_trap'], t_qs, vC_qs)
        
        # MAPE Euler
        e_iL_eul = np.mean(np.abs((dados['iL_eul'] - iL_qs_interp_eul) / np.maximum(np.abs(iL_qs_interp_eul), eps))) * 100
        e_vC_eul = np.mean(np.abs((dados['vC_eul'] - vC_qs_interp_eul) / np.maximum(np.abs(vC_qs_interp_eul), eps))) * 100
        
        # MAPE Trapézio
        e_iL_trap = np.mean(np.abs((dados['iL_trap'] - iL_qs_interp_trap) / np.maximum(np.abs(iL_qs_interp_trap), eps))) * 100
        e_vC_trap = np.mean(np.abs((dados['vC_trap'] - vC_qs_interp_trap) / np.maximum(np.abs(vC_qs_interp_trap), eps))) * 100
        
        err_iL_eul.append(e_iL_eul)
        err_vC_eul.append(e_vC_eul)
        err_iL_trap.append(e_iL_trap)
        err_vC_trap.append(e_vC_trap)

    # Plotagem
    fig, (ax_iL, ax_vC) = plt.subplots(1, 2, figsize=(14, 6))
    
    ax_iL.plot(n_sorted, err_iL_eul, marker='o', linestyle='-', label='Euler')
    ax_iL.plot(n_sorted, err_iL_trap, marker='s', linestyle='-', label='Trapézio')
    ax_iL.set_title('Corrente $i_L$', fontsize=FONT_TITLE)
    ax_iL.set_xticks(F_MULTIPLIER)
    ax_iL.set_xlabel('Fator n', fontsize=FONT_LABEL)
    ax_iL.set_ylabel('Erro (%)', fontsize=FONT_LABEL)
    
    ax_vC.plot(n_sorted, err_vC_eul, marker='o', linestyle='-', label='Euler')
    ax_vC.plot(n_sorted, err_vC_trap, marker='s', linestyle='-', label='Trapézio')
    ax_vC.set_title('Tensão $v_C$', fontsize=FONT_TITLE)
    ax_vC.set_xlabel('Fator n', fontsize=FONT_LABEL)
    ax_vC.set_ylabel('Erro (%)', fontsize=FONT_LABEL)
    
    for ax in [ax_iL, ax_vC]:
        ax.grid(True)
        ax.legend(fontsize=FONT_LEGEND)
        ax.tick_params(axis='both', labelsize=FONT_TICKS)
    
    fig.tight_layout()
    fig.savefig('erro_relativo_completo.png', dpi=DPI)
    plt.close(fig)

def gerar_graficos_comparativos(resultados_sim, t_qs, var_qs, nome_var, ylabel, filename, xlim=None):
    """
    Função utilitária para gerar e salvar gráficos duplos (Euler e Trapézio)
    evitando a repetição massiva de código.
    """
    fig, (ax_eul, ax_trap) = plt.subplots(1, 2, figsize=(14, 8))
    
    # Configuração base dos eixos
    for ax in [ax_eul, ax_trap]:
        ax.set_ylabel(ylabel, fontsize=FONT_LABEL)
        ax.set_xlabel('Tempo [ms]', fontsize=FONT_LABEL)
        ax.grid(True)
        ax.tick_params(axis='both', labelsize=FONT_TICKS)
        if xlim:
            ax.set_xlim(xlim)
            
    ax_eul.set_title('Método de Euler', fontsize=FONT_TITLE)
    ax_trap.set_title('Método do Trapézio', fontsize=FONT_TITLE)

    # Plotando os resultados das simulações iterativas
    for n in sorted(resultados_sim.keys()):
        dados = resultados_sim[n]
        
        ax_eul.plot(dados['t_eul'] * 1000, dados[f'{nome_var}_eul'], label=f'n={n}', alpha=0.8)
        ax_trap.plot(dados['t_trap'] * 1000, dados[f'{nome_var}_trap'], label=f'n={n}', alpha=0.8)

    # Plotando linha base do QSpice
    qs_style = {'color': 'black', 'linewidth': 1.1, 'linestyle': '-', 'alpha': 0.5, 'label': 'QSpice'}
    ax_eul.plot(t_qs * 1000, var_qs, **qs_style)
    ax_trap.plot(t_qs * 1000, var_qs, **qs_style)

    # Inserindo legendas
    ax_eul.legend(loc='lower right', fontsize=FONT_LEGEND)
    ax_trap.legend(loc='lower right', fontsize=FONT_LEGEND)

    fig.tight_layout()
    fig.savefig(filename, dpi=DPI)
    plt.close(fig)

# ==========================================================
# FUNÇÃO PRINCIPAL (ORQUESTRADOR)
# ==========================================================
def main():
    # 1. Carregamento dos dados do QSpice
    try:
        qspice_data = np.loadtxt('buck.csv', delimiter=',', skiprows=1)
        t_qs = qspice_data[:, 0]  
        vC_qs = qspice_data[:, 1] 
        iL_qs = qspice_data[:, 2] 
    except FileNotFoundError:
        print("Arquivo 'buck.csv' não encontrado. Certifique-se de que ele está na mesma pasta.")
        return

    # 2. Execução das Simulações (Feito apenas UMA VEZ e armazenado)
    resultados_sim = {}
    for n in F_MULTIPLIER:
        t_eul, iL_eul, vC_eul = buck_euler_discretization(n)
        t_trap, iL_trap, vC_trap = buck_trapezium_discretization(n)
        resultados_sim[n] = {
            't_eul': t_eul, 'iL_eul': iL_eul, 'vC_eul': vC_eul,
            't_trap': t_trap, 'iL_trap': iL_trap, 'vC_trap': vC_trap
        }

    # 3. Cálculo e Plotagem dos Erros (Reaproveitando os resultados calculados acima)
    plot_erro_relativo_medio(resultados_sim, t_qs, iL_qs, vC_qs)

    # 4. Geração dos Gráficos de Corrente e Tensão (Utilizando a função genérica)
    graficos = [
        # (var_qs, nome_var, ylabel, filename, xlim)
        (iL_qs, 'iL', 'Corrente [A]', 'corrente_completa.png', None),
        (vC_qs, 'vC', 'Tensão [V]', 'tensao_completa.png', None),
        (iL_qs, 'iL', 'Corrente [A]', 'corrente_permanente.png', (0.2, 0.225)),
        (vC_qs, 'vC', 'Tensão [V]', 'tensao_permanente.png', (0.2, 0.225)),
        (iL_qs, 'iL', 'Corrente [A]', 'corrente_trans.png', (0.0, 0.12)),
        (vC_qs, 'vC', 'Tensão [V]', 'tensao_trans.png', (0.0, 0.12))
    ]

    for dados_qs, nome_var, ylabel, filename, limite_x in graficos:
        gerar_graficos_comparativos(
            resultados_sim=resultados_sim,
            t_qs=t_qs,
            var_qs=dados_qs,
            nome_var=nome_var,
            ylabel=ylabel,
            filename=filename,
            xlim=limite_x
        )

    print("Todas as simulações e gráficos foram gerados com sucesso!")

if __name__ == "__main__":
    main()